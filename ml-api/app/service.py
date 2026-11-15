"""Model loading and inference. The models are the tested ones in ml/artifacts/final_model, loaded once at startup with
the project's own fs_ml code (same feature order, same projection code as the notebooks). Nothing is trained here."""
from __future__ import annotations

import hashlib
import json
import logging
import math
import sys
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import settings

log = logging.getLogger("ml-api")
TARGET_MEANING = {
    "sm_root_monthly": "Root-zone soil water, ERA5-Land layer 3 (28-100 cm), monthly mean, volumetric (m3 of water per m3 of soil)",
    "ndvi_quarterly": "Plant greenness (NDVI) of the quarter, from the team's satellite composite (-1 to 1)",
}
EL_NINO_YEARS = [1998, 2016, 2017, 2023, 2024]   # rule in docs/ML_PROJECTIONS.md: Niño 1+2 > +1.0 °C in Jan-Apr
# Physical limits: values outside are impossible, not just unusual (unusual values only raise a warning)
PHYSICAL = [("rain", 0, 3000), ("pet", 0, 1500), ("rh2m", 0, 100), ("ws2m", 0, 60), ("allsky", 0, 50), ("t2m", -40, 60),
            ("sm_", 0, 1), ("ndvi", -1, 1), ("month_", -1, 1), ("quarter", 1, 4)]


class ModelUnavailable(RuntimeError):
    pass


@dataclass
class State:
    models: dict
    cube: object
    proj_card: dict
    sha: dict
    skill: pd.DataFrame
    bundle: dict | None = None      # projections of the whole grid, computed once at startup


STATE: State | None = None
LOAD_ERROR: str | None = None


def _sha(p) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load() -> None:
    """Called once at startup. Keeps the error (instead of crashing) so /health can report it."""
    global STATE, LOAD_ERROR
    try:
        for p in (settings.model_dir, settings.ml_package_dir / "fs_ml", settings.cube_path, settings.projection_card):
            if not p.exists():
                raise FileNotFoundError(f"missing: {p.name} (see README: paths and FS_* variables)")
        sys.path.insert(0, str(settings.ml_package_dir))
        from fs_ml.predict import load as load_model
        from fs_ml import project as P

        models, sha = {}, {}
        for name in ("sm_root_monthly", "ndvi_quarterly"):
            m = load_model(name, settings.model_dir)       # asserts the booster's feature names = preprocessing order
            sha[name] = _sha(settings.model_dir / name / "model.ubj")
            if sha[name] != m["card"]["sha256"]:
                raise RuntimeError(f"{name}: model file does not match its model card (sha256)")
            models[name] = m
        z = np.load(settings.cube_path, allow_pickle=False)
        cells = pd.DataFrame({"cell_id": z["cell_id"], "lat": z["lat"], "lon": z["lon"], "province": z["province"],
                              "district": z["district"], **{k.split("__")[1]: z[k] for k in z.files if k.startswith("soil__")}})
        cube = P.Cube(cells=cells, dates=pd.DatetimeIndex(pd.to_datetime(z["dates"])),
                      v={k.split("__")[1]: z[k].astype(float) for k in z.files if k.startswith("v__")},
                      quarters=pd.PeriodIndex(z["quarters"], freq="Q"), ndvi=z["ndvi"].astype(float))
        skill = pd.read_csv(settings.projection_card.with_name("hindcast_skill_by_lead.csv"))
        STATE = State(models=models, cube=cube, proj_card=json.loads(settings.projection_card.read_text()), sha=sha, skill=skill)
        STATE.bundle = build_bundle(STATE)
        LOAD_ERROR = None
        log.info("models loaded: %s | cube: %d cells, %s to %s", {k: v[:12] for k, v in sha.items()}, len(cells),
                 cube.dates[0].date(), cube.dates[-1].date())
    except Exception as e:    # reported by /health and as 503, never hidden
        STATE, LOAD_ERROR = None, f"{type(e).__name__}: {e}"
        log.exception("model loading failed")


def state() -> State:
    if STATE is None:
        raise ModelUnavailable(LOAD_ERROR or "models not loaded")
    return STATE


# ---------- model info ----------

def model_info() -> dict:
    s = state()
    out = {}
    for name, m in s.models.items():
        c = m["card"]
        out[name] = {
            "name": name, "algorithm": "XGBoost", "estimator": c.get("estimator"), "version": c.get("version"),
            "sha256": s.sha[name], "target": c["target"] | {"meaning": TARGET_MEANING[name]},
            "features_in_order": m["features"], "hyperparameters": c.get("hyperparameters"), "trees": c.get("trees"),
            "training_date": None,
            "training_date_note": "Not stored in the model files. Trained on 1998-2017 data; artifacts committed on 2026-11-15 (git history).",
            "data": c.get("data"), "metrics": c.get("metrics"), "baseline_to_beat": c.get("baseline_to_beat"),
            "test_verdict": c.get("test_verdict"), "interval": {k: m["intervals"].get(k) for k in ("method", "nominal", "half_width_90_by_season", "tested_coverage")},
            "intended_use": c.get("intended_use"), "known_limitations": c.get("not_for"),
            "library_versions": c.get("library_versions"),
        }
    pc = s.proj_card
    out["projections"] = {"method": pc["method"], "useful_lead": pc["useful_lead"], "coverage_2023_2025": pc["coverage_2023_2025"],
                          "scenario_checks": pc["scenario_checks"], "not_for": pc["not_for"]}
    return out


# ---------- single prediction ----------

def _season(name, f):
    if name == "sm_root_monthly":
        month = round(math.atan2(f["month_sin"], f["month_cos"]) * 6 / math.pi) % 12 or 12
        return "wet Jan-Apr" if month <= 4 else "dry May-Dec"
    return f"Q{int(f['quarter'])}"


def validate_features(name: str, feats: dict) -> list[str]:
    """Exact training names, nothing extra, nothing missing; null only where training had missing values. Returns the
    list of problems (empty = valid)."""
    m = state().models[name]
    expected, problems = m["features"], []
    missing = [f for f in expected if f not in feats]
    extra = [f for f in feats if f not in expected]
    if missing: problems.append(f"missing features: {missing}")
    if extra: problems.append(f"unknown features: {extra}")
    for f, v in feats.items():
        if f not in expected: continue
        if v is None:
            if m["bounds"][f]["missing_share"] == 0:
                problems.append(f"{f} cannot be null (it was never missing in training)")
            continue
        for key, lo, hi in PHYSICAL:
            if key in f and not (lo <= v <= hi):
                problems.append(f"{f}={v} is outside the physical range [{lo}, {hi}]")
                break
    if name == "ndvi_quarterly" and feats.get("quarter") not in (None, 1, 2, 3, 4) and "quarter" in feats:
        problems.append("quarter must be 1, 2, 3 or 4")
    return problems


def predict_one(name: str, feats: dict) -> dict:
    m = state().models[name]
    X = pd.DataFrame([{f: (np.nan if feats[f] is None else feats[f]) for f in m["features"]}])[m["features"]]
    pred = float(m["model"].predict(X)[0])
    season = _season(name, feats)
    half = m["intervals"]["half_width_90_by_season"][season]
    soft = [f for f, b in m["bounds"].items() if feats[f] is not None and not (b["p01"] <= feats[f] <= b["p99"])]
    hard = [f for f, b in m["bounds"].items() if feats[f] is not None and not (b["min"] <= feats[f] <= b["max"])]
    warns = []
    if hard: warns.append("Some inputs are outside anything seen in training (1998-2017): the prediction is an extrapolation.")
    elif soft: warns.append("Some inputs are unusual for training (outside p01-p99): read the prediction with extra care.")
    tc = m["intervals"].get("tested_coverage", {})
    return {"model": name, "target": m["card"]["target"] | {"meaning": TARGET_MEANING[name]}, "prediction": pred,
            "interval_90": {"low": pred - half, "high": pred + half, "nominal": 0.9,
                            "method": f"split conformal, one width per season ({season}), calibrated on 2018-2022",
                            "tested_coverage": tc.get("by_season_90")},
            "out_of_training_range": soft, "far_out_of_training_range": hard,
            "missing_features": [f for f in m["features"] if feats[f] is None], "warnings": warns}


# ---------- climate simulation ----------

def find_cell(loc) -> int:
    c = state().cube.cells
    if loc.cell_id is not None:
        hit = np.flatnonzero(c.cell_id.to_numpy() == loc.cell_id)
        if not len(hit):
            raise LookupError(f"cell {loc.cell_id} is not in the Lambayeque grid")
        return int(hit[0])
    step = 0.017966305682390427
    cid = f"{math.floor(loc.lon / step)},{math.floor(loc.lat / step)}"
    hit = np.flatnonzero(c.cell_id.to_numpy() == cid)
    if not len(hit):
        raise LookupError("that point is outside the Lambayeque 2 km grid")
    return int(hit[0])


def simulate(req) -> dict:
    from fs_ml import project as P
    s = state(); cube, m = s.cube, s.models["sm_root_monthly"]
    i = find_cell(req.location)
    start = pd.Timestamp(req.start + "-01")
    if start not in cube.dates or cube.t(start) < 4:
        raise ValueError(f"start must be between {cube.dates[4]:%Y-%m} and {cube.dates[-1]:%Y-%m}")
    if np.isnan(cube.v["sm_root_m3m3"][i, cube.t(start)]):
        raise LookupError("this cell has no observed soil water at the start month (a coastal cell without ERA5-Land)")
    sc, H = req.scenario, req.horizon
    one = P.Cube(cells=cube.cells.iloc[[i]].reset_index(drop=True), dates=cube.dates,
                 v={k: v[[i]] for k, v in cube.v.items()}, quarters=cube.quarters, ndvi=cube.ndvi[[i]])
    w_all = P.analog_weather(one, start, H, range(1998, cube.dates[-1].year + 1))
    years = EL_NINO_YEARS if sc.analog == "el_nino" else (list(range(1998, 2100)) if sc.analog == "all" else sc.analog)
    w = P.select_members(w_all, years)
    changed = []
    if sc.rain_factor != 1 or sc.t2m_delta != 0 or sc.rh_delta != 0:
        w = P.scenario_adjust(w, sc.rain_factor, sc.t2m_delta, sc.rh_delta, sc.months)
        where = "all months" if not sc.months else f"lead months {sc.months}"
        if sc.rain_factor != 1: changed.append(f"rain_mm × {sc.rain_factor:g} ({where})")
        if sc.t2m_delta: changed.append(f"t2m_c {sc.t2m_delta:+g} °C ({where}; potential evaporation unchanged)")
        if sc.rh_delta: changed.append(f"power_rh2m_pct {sc.rh_delta:+g} points ({where})")
    if sc.dry_months:
        w = P.scenario_drought(w, sc.dry_months, one, start)
        changed.append(f"no rain and driest surface soil in lead months {sc.dry_months}")
    if sc.analog != "all":
        changed.append(f"weather years limited to {sorted(int(y) for y in w['years'])}")

    base = P.project_sm(m, one, start, H, None, weather=w_all)["members"][:, 0, :]
    alt = P.project_sm(m, one, start, H, None, weather=w)["members"][:, 0, :]
    corr = np.array([s.proj_card["correction_by_lead"]["sm"][str(k)] for k in range(1, H + 1)])
    def band(mem):
        lo, med, hi = np.quantile(mem, [0.05, 0.5, 0.95], axis=0)
        return med, np.clip(lo - corr, 0, None), hi + corr
    bm, bl, bh = band(base); am, al, ah = band(alt)
    dates = pd.date_range(start + pd.DateOffset(months=1), periods=H, freq="MS")
    rmse = m["card"]["metrics"]["validation_2018_2022"]["RMSE"]["value"]
    useful = s.proj_card["useful_lead"]["soil_water_months"]
    comp = []
    for k in range(H):
        d = float(am[k] - bm[k])
        comp.append({"period": f"{dates[k]:%Y-%m}", "lead": k + 1, "absolute_difference": d,
                     "percentage_change": d / bm[k] * 100 if bm[k] > 1e-6 else None,
                     "direction": "increased" if d > 1e-4 else "decreased" if d < -1e-4 else "unchanged",
                     "within_model_error": abs(d) < rmse, "within_useful_lead": k + 1 <= useful})
    ood = P.out_of_training_range(w, m["bounds"])

    # reliability and a summary written only from the numbers above
    rain_only = sc.rain_factor != 1 and not sc.dry_months
    big = max(comp, key=lambda r: abs(r["absolute_difference"]))
    n_up = sum(r["direction"] == "increased" for r in comp); n_down = sum(r["direction"] == "decreased" for r in comp)
    if not changed:
        summary = "No input was changed: the scenario equals the baseline (a normal year)."
    elif all(r["within_model_error"] for r in comp):
        summary = (f"With these changes the model's median root-zone soil water moves by at most {abs(big['absolute_difference']):.4f} m3/m3 "
                   f"(in {big['period']}), less than its typical error ({rmse:.4f}): the model shows no clear change.")
    else:
        pct = f" ({big['percentage_change']:+.0f} %)" if big["percentage_change"] is not None else ""
        summary = (f"With these changes the model's median root-zone soil water is higher than in a normal year in {n_up} of {H} months "
                   f"and lower in {n_down}. The biggest difference is {big['absolute_difference']:+.4f} m3/m3{pct} in {big['period']}.")
    limits = ["A model answer to a made-up situation, not a forecast and not proof of cause and effect.",
              f"Projections beat 'a typical year' only for the first {useful} months (hindcasts 2018-2022).",
              f"In 2023-2025 the 90 % range held the real value {s.proj_card['coverage_2023_2025']['sm']['coverage_90']:.0%} of the time: ranges are too narrow in El Niño years.",
              "One 2 km cell; no irrigation in the data; no crop yield."]
    if rain_only:
        limits.insert(0, "Rain-only changes failed the pre-registered sanity checks: the model barely reacts to rain alone (it leans on last month's soil water), and can move in the wrong direction. Treat small differences as noise.")
    if sc.t2m_delta or sc.rh_delta:
        limits.insert(0, "Temperature or humidity changes do not recompute evaporation or surface soil water: only the model's direct response is shown.")
    if len(w["years"]) < 10:
        limits.append(f"Only {len(w['years'])} weather years in this scenario: the range is less reliable.")
    if any(v > 0 for v in ood.values()):
        limits.append("Some changed inputs are outside anything seen in training: there the model extrapolates.")

    cell = one.cells.iloc[0]
    as_list = lambda a: [round(float(x), 5) for x in a]
    return {
        "location": {"cell_id": cell.cell_id, "lat": float(cell.lat), "lon": float(cell.lon), "province": cell.province,
                     "district": cell.district or None, "cell_size_km": 2},
        "start": req.start, "model": {"algorithm": "XGBoost", "name": "sm_root_monthly", "status": "available", "sha256": s.sha["sm_root_monthly"]},
        "target": m["card"]["target"] | {"meaning": TARGET_MEANING["sm_root_monthly"]},
        "periods": [f"{d:%Y-%m}" for d in dates],
        "baseline": {"median": as_list(bm), "low_90": as_list(bl), "high_90": as_list(bh), "members": len(w_all["years"]),
                     "analog_years": [int(y) for y in w_all["years"]]},
        "scenario": {"median": as_list(am), "low_90": as_list(al), "high_90": as_list(ah), "members": len(w["years"]),
                     "analog_years": [int(y) for y in w["years"]]},
        "comparison": comp, "modified_inputs": changed, "out_of_training_range": ood,
        "reliability": {"useful_lead_months": useful, "model_rmse_validation": rmse,
                        "range_coverage_2023_2025": s.proj_card["coverage_2023_2025"]["sm"]["coverage_90"],
                        "rain_only_change": rain_only, "scenario_checks": s.proj_card["scenario_checks"]},
        "interpretation": {"summary": summary, "limitations": limits},
    }


# ---------- projections of the whole grid (the "What's ahead" screens) ----------

K = 1000                                   # values are sent as integers x 1000 to keep the payload small
DRY_SEASON = [6, 7, 8, 9, 10]               # Jul..Nov when the start is December


def build_bundle(s: State) -> dict:
    """Run the tested models over every Lambayeque cell from the last observed month, for the scenarios that passed
    their checks (docs/ML_PROJECTIONS.md): a normal year (all weather years), El Niño years, and two dry months.
    Same code, analog years and range corrections as ml/notebooks/06_projections.ipynb."""
    import time
    import warnings
    from fs_ml import project as P
    warnings.filterwarnings("ignore", message="(All-NaN slice|Mean of empty slice)")   # cells/quarters with no data stay null
    t0 = time.time()
    cube, sm_m, nd_m = s.cube, s.models["sm_root_monthly"], s.models["ndvi_quarterly"]
    start = cube.dates[-1]
    valid = ~np.isnan(cube.v["sm_root_m3m3"][:, cube.t(start)])
    W = P.analog_weather(cube, start, 12, range(1998, start.year + 1))
    dry_names = [f"{(start + pd.DateOffset(months=k)):%b}" for k in (2, 3)]
    scen = {"base": (W, f"the weather of each past year {W['years'][0]}-{W['years'][-1]}, one by one"),
            "el_nino": (P.select_members(W, EL_NINO_YEARS), f"only coastal El Niño years {EL_NINO_YEARS}"),
            "drought_feb_mar": (P.scenario_drought(W, [2, 3], cube, start), f"no rain and the driest surface soil in {' and '.join(dry_names)}")}
    corr = {v: np.array([s.proj_card["correction_by_lead"][key][str(k)] for k in range(1, n + 1)])
            for v, key, n in (("soil_water", "sm", 12), ("ndvi", "ndvi", 4))}
    out = {"soil_water": {}, "ndvi": {}}
    flat = lambda a: [None if not np.isfinite(x) else int(round(x * K)) for x in np.asarray(a, float).reshape(-1)]
    for name, (w, _) in scen.items():
        sm = P.project_sm(sm_m, cube, start, 12, None, weather=w)
        nd = P.project_ndvi(nd_m, cube, sm)
        for v, run, lo_clip, hi_clip in (("soil_water", sm, 0, 1), ("ndvi", nd, -1, 1)):
            mem = run["members"][:, valid, :]
            lo, med, hi = np.quantile(mem, [0.05, 0.5, 0.95], axis=0)
            item = {"median": flat(med), "members": int(mem.shape[0])}
            if name in ("base", "el_nino"):     # ensembles of real years: their 90 % range is meaningful
                item |= {"low": flat(np.clip(lo - corr[v], lo_clip, hi_clip)), "high": flat(np.clip(hi + corr[v], lo_clip, hi_clip))}
            out[v][name] = item
        if name == "base":
            sm_dates, nd_quarters = sm["dates"], nd["quarters"]
    cells = cube.cells[valid].reset_index(drop=True)
    xy = cells.cell_id.str.split(",", expand=True).astype(int)
    # usual value: observed mean 1998-<last year> per cell and calendar month (soil water) or quarter (NDVI)
    smv = cube.v["sm_root_m3m3"][valid]
    out["soil_water"]["usual"] = flat(np.stack([np.nanmean(smv[:, cube.dates.month == d.month], axis=1) for d in sm_dates], axis=1))
    qq = np.array([q.quarter for q in cube.quarters]); ndv = cube.ndvi[valid]
    with np.errstate(all="ignore"):
        out["ndvi"]["usual"] = flat(np.stack([np.nanmean(ndv[:, qq == q.quarter], axis=1) for q in nd_quarters], axis=1))
    provinces = sorted(cells.province.unique()); districts = sorted(d for d in cells.district.unique() if d)
    # district summary: median over cells of the dry-season soil water and the second-half greenness
    summary = []
    for name in scen:
        a = np.array(out["soil_water"][name]["median"], float).reshape(len(cells), 12)[:, DRY_SEASON].mean(axis=1)
        b = np.array([np.nan if x is None else x for x in out["ndvi"][name]["median"]], float).reshape(len(cells), 4)[:, 2:].mean(axis=1)
        for d in districts:
            m = (cells.district == d).to_numpy()
            summary.append({"district": d, "scenario": name, "cells": int(m.sum()), "dry_season_soil_water": int(round(np.median(a[m]))),
                            "q3q4_ndvi": None if np.isnan(b[m]).all() else int(round(np.nanmedian(b[m])))})
    sk = lambda v: [{"lead": int(r.lead), "skill": round(r.skill, 3), "low": round(r.skill_ci_low, 3), "high": round(r.skill_ci_high, 3)}
                    for r in s.skill[(s.skill.variable == v) & (s.skill.period == "validation")].itertuples()]
    base_sm = np.array([x for x in out["soil_water"]["base"]["median"] if x is not None])
    base_nd = np.array([x for x in out["ndvi"]["base"]["median"] if x is not None])
    bundle = {
        "meta": {"start": f"{start:%Y-%m}", "scale": K, "grid_step_deg": 0.017966305682390427,
                 "periods": {"soil_water": [f"{d:%Y-%m}" for d in sm_dates], "ndvi": [str(q) for q in nd_quarters]},
                 "useful_lead": s.proj_card["useful_lead"], "skill_by_lead": {"soil_water": sk("sm"), "ndvi": sk("ndvi")},
                 "coverage_2023_2025": {k: round(v["coverage_90"], 3) for k, v in s.proj_card["coverage_2023_2025"].items()},
                 "scenarios": {k: d for k, (_, d) in scen.items()},
                 "domain": {"soil_water": [int(np.percentile(base_sm, 2)), int(np.percentile(base_sm, 98))],
                            "ndvi": [int(np.percentile(base_nd, 2)), int(np.percentile(base_nd, 98))]},
                 "models": {k: v[:16] for k, v in s.sha.items()}, "not_for": s.proj_card["not_for"],
                 "computed_by": "ml-api at startup with the tested XGBoost models"},
        "cells": {"x": xy[0].tolist(), "y": xy[1].tolist(), "province": [provinces.index(p) for p in cells.province],
                  "district": [districts.index(d) if d else -1 for d in cells.district]},
        "provinces": provinces, "districts": districts, **out, "district_summary": summary,
    }
    log.info("projections computed for %d cells and %d scenarios in %.1f s", len(cells), len(scen), time.time() - t0)
    return bundle


def projections() -> dict:
    return state().bundle


def projection_at(loc, variable: str, scenario: str) -> dict:
    """The series of one cell, in real units (the same numbers as the bundle)."""
    b = state().bundle
    if variable not in ("soil_water", "ndvi") or scenario not in b[variable]:
        raise ValueError("variable must be soil_water or ndvi; scenario one of " + ", ".join(k for k in b["soil_water"] if k != "usual"))
    step = b["meta"]["grid_step_deg"]
    x, y = (math.floor(loc.lon / step), math.floor(loc.lat / step)) if loc.cell_id is None else map(int, loc.cell_id.split(","))
    hit = [i for i, (a, c) in enumerate(zip(b["cells"]["x"], b["cells"]["y"])) if a == x and c == y]
    if not hit:
        raise LookupError("no projection for that point (outside the Lambayeque grid, or a cell without data)")
    i, n = hit[0], len(b["meta"]["periods"][variable])
    get = lambda arr: None if arr is None else [None if v is None else v / K for v in arr[i * n:(i + 1) * n]]
    item = b[variable][scenario]
    return {"cell_id": f"{x},{y}", "variable": variable, "scenario": scenario, "periods": b["meta"]["periods"][variable],
            "median": get(item["median"]), "low_90": get(item.get("low")), "high_90": get(item.get("high")),
            "usual": get(b[variable]["usual"]), "members": item["members"],
            "useful_lead": b["meta"]["useful_lead"]["soil_water_months" if variable == "soil_water" else "ndvi_quarters"]}
