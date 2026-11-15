"""One scenario engine for every simulation (roadmap §7). Each typed endpoint only builds a configuration.

Flow: observed state of the cell at `start` → baseline = the weather of each past year for the coming months →
change only what was asked → soil water month by month (the predicted value feeds the next month) → NDVI on whole
quarters → differences → 90 % bands (members + conformal correction per lead from the Validation hindcasts) →
training-domain check → reliability level, warnings and a summary written only from the numbers."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import state
from .common import EL_NINO_YEARS, LRU, TARGET_MEANING, make_id, warn, worst
from .prediction import cell_info, find_cell, outside_warning
from .common import NotFound, BadRequest

RESULTS = LRU(500)                 # simulation_id -> response

# Which Phase 2 check (docs/ML_API_VALIDATION.md) a kind of change depends on
CHECK_OF = {"temperature": "S1", "drought": "S2", "rainfall": "S3", "recovery": "S4"}


def _changes(cfg) -> dict:
    """What the configuration changes, by kind."""
    rain_only = cfg.rain_factor != 1
    return {"drought": bool(cfg.dry_months), "rainfall": rain_only, "temperature": cfg.t2m_delta != 0,
            "humidity": cfg.rh_delta != 0, "evaporation": getattr(cfg, "pet_factor", 1) != 1,
            "wind": getattr(cfg, "ws_delta", 0) != 0, "sunlight": getattr(cfg, "allsky_delta", 0) != 0,
            "el_nino": cfg.analog == "el_nino", "years": isinstance(cfg.analog, list)}


def consistency_warnings(cfg) -> list[dict]:
    """Combinations that are physically odd: warned, not blocked (impossible values are already 422)."""
    out = []
    pet, rh, sun = getattr(cfg, "pet_factor", 1), cfg.rh_delta, getattr(cfg, "allsky_delta", 0)
    if cfg.t2m_delta > 0 and pet < 1:
        out.append(warn("inconsistent", "Warmer weather with less evaporation is physically unusual.", ["t2m_c", "pet_mm"]))
    if cfg.t2m_delta < 0 and pet > 1:
        out.append(warn("inconsistent", "Cooler weather with more evaporation is physically unusual.", ["t2m_c", "pet_mm"]))
    if cfg.rain_factor > 1 and (sun > 0 or rh < 0):
        out.append(warn("inconsistent", "More rain usually comes with more clouds and humidity, not more sun or drier air.", ["rain_mm", "power_allsky_mj_m2_day", "power_rh2m_pct"]))
    if (cfg.rain_factor == 0 or cfg.dry_months) and rh > 10:
        out.append(warn("inconsistent", "Months without rain with much more humid air are physically unusual.", ["rain_mm", "power_rh2m_pct"]))
    return out


def _band(mem, corr, lo_clip, hi_clip):
    lo, med, hi = np.quantile(mem, [0.05, 0.5, 0.95], axis=0)
    return med, np.clip(lo - corr, lo_clip, hi_clip), np.clip(hi + corr, lo_clip, hi_clip)


def _compare(labels, base, alt, err, useful):
    out = []
    for k, lab in enumerate(labels):
        d = float(alt[k] - base[k])
        out.append({"period": lab, "lead": k + 1, "absolute_difference": d,
                    "percentage_change": d / base[k] * 100 if abs(base[k]) > 1e-6 else None,
                    "direction": "increased" if d > 1e-4 else "decreased" if d < -1e-4 else "unchanged",
                    "within_model_error": abs(d) < err, "within_useful_lead": k + 1 <= useful})
    return out


def run(location, start: str, horizon: int, cfg, kind: str = "climate", include_ndvi: bool = True, request: dict | None = None) -> dict:
    from fs_ml import project as P
    s = state.get(); cube = s.cube; nd_m = s.models["ndvi_quarterly"]
    sm_m = s.sim                     # v3 (ERA5-Land rain, monotone) when accepted, else v1: its own corrections and checks
    i = find_cell(location)
    t0 = pd.Timestamp(start + "-01")
    if t0 not in cube.dates or cube.t(t0) < 4:
        raise BadRequest(f"start must be between {cube.dates[4]:%Y-%m} and {cube.dates[-1]:%Y-%m}")
    if np.isnan(cube.v["sm_root_m3m3"][i, cube.t(t0)]):
        raise NotFound("this cell has no observed soil water at the start month (a coastal cell without ERA5-Land)")
    sid = make_id("sim", {"kind": kind, "sim_model": sm_m["sha256"], **(request or {})}, s.sha)
    hit = RESULTS.get(sid)
    if hit:
        return hit

    one = P.Cube(cells=cube.cells.iloc[[i]].reset_index(drop=True), dates=cube.dates, v={k: v[[i]] for k, v in cube.v.items()},
                 quarters=cube.quarters, ndvi=cube.ndvi[[i]])
    w_all = P.analog_weather(one, t0, horizon, range(1998, cube.dates[-1].year + 1))
    years = EL_NINO_YEARS if cfg.analog == "el_nino" else (list(range(1998, 2100)) if cfg.analog == "all" else cfg.analog)
    w = P.select_members(w_all, years)
    changed = []
    where = "all months" if not cfg.months else f"lead months {cfg.months}"
    pet, ws, sun = getattr(cfg, "pet_factor", 1.0), getattr(cfg, "ws_delta", 0.0), getattr(cfg, "allsky_delta", 0.0)
    if any([cfg.rain_factor != 1, cfg.t2m_delta, cfg.rh_delta, pet != 1, ws, sun]):
        w = P.scenario_adjust(w, cfg.rain_factor, cfg.t2m_delta, cfg.rh_delta, cfg.months, pet, ws, sun)
        for cond, txt in [(cfg.rain_factor != 1, f"rain_mm × {cfg.rain_factor:g}"), (cfg.t2m_delta, f"t2m_c {cfg.t2m_delta:+g} °C (evaporation not recomputed)"),
                          (cfg.rh_delta, f"power_rh2m_pct {cfg.rh_delta:+g} points"), (pet != 1, f"pet_mm × {pet:g}"),
                          (ws, f"power_ws2m_ms {ws:+g} m/s"), (sun, f"power_allsky_mj_m2_day {sun:+g} MJ/m²/day")]:
            if cond: changed.append(f"{txt} ({where})")
    if cfg.dry_months:
        w = P.scenario_drought(w, cfg.dry_months, one, t0)
        changed.append(f"no rain and driest surface soil in lead months {cfg.dry_months}")
    if cfg.analog != "all":
        changed.append(f"weather years limited to {sorted(int(y) for y in w['years'])}")

    # soil water, month by month
    base_run, alt_run = P.project_sm(sm_m, one, t0, horizon, None, weather=w_all), P.project_sm(sm_m, one, t0, horizon, None, weather=w)
    corr_sm = np.array([sm_m["corr"][k] for k in range(1, horizon + 1)])
    bm, bl, bh = _band(base_run["members"][:, 0, :], corr_sm, 0, 1)
    am, al, ah = _band(alt_run["members"][:, 0, :], corr_sm, 0, 1)
    labels = [f"{d:%Y-%m}" for d in base_run["dates"]]
    rmse, useful = sm_m["rmse"], sm_m["useful"]
    comp = _compare(labels, bm, am, rmse, useful)

    # NDVI on whole quarters (needs a start at the end of a quarter)
    ndvi = None
    if include_ndvi and t0.month % 3 == 0 and horizon >= 3:
        nb, na = P.project_ndvi(nd_m, one, base_run), P.project_ndvi(nd_m, one, alt_run)
        nq = nb["members"].shape[2]
        corr_nd = np.array([s.proj["corr_nd"][k] for k in range(1, nq + 1)])     # NDVI fed with this soil water model
        qb = _band(nb["members"][:, 0, :], corr_nd, -1, 1); qa = _band(na["members"][:, 0, :], corr_nd, -1, 1)
        qlabels = [str(q) for q in nb["quarters"]]
        nd_err = nd_m["card"]["metrics"]["validation_2018_2022"]["RMSE"]["value"]
        ndvi = {"periods": qlabels, "unit": "NDVI",
                "baseline": {"median": _r(qb[0]), "low_90": _r(qb[1]), "high_90": _r(qb[2])},
                "scenario": {"median": _r(qa[0]), "low_90": _r(qa[1]), "high_90": _r(qa[2])},
                "comparison": _compare(qlabels, qb[0], qa[0], nd_err, s.proj["useful_lead"]["ndvi_quarters"])}

    # domain, reliability, warnings
    hard, soft = P.out_of_training_range(w, sm_m["bounds"]), P.out_of_training_range(w, sm_m["bounds"], soft=True)
    ch = _changes(cfg)
    warnings, level = consistency_warnings(cfg), "ok"
    if warnings: level = "warning"
    warnings += outside_warning(i)
    if any(v > 0 for v in soft.values()):
        warnings.append(warn("out_of_range", "Some scenario inputs are unusual for training (outside p01-p99).", [k for k, v in soft.items() if v > 0])); level = worst(level, "warning")
    if any(v > 0 for v in hard.values()):
        warnings.append(warn("out_of_domain", "Some scenario inputs are outside anything seen in training: the model extrapolates there.", [k for k, v in hard.items() if v > 0])); level = worst(level, "out_of_domain")
    if horizon > useful:
        warnings.append(warn("beyond_useful_lead", f"Beyond {useful} months the projection is close to a typical year.", labels[useful:])); level = worst(level, "warning")
    if len(w["years"]) < 10:
        warnings.append(warn("few_analogs", f"Only {len(w['years'])} weather years in this scenario: the range is less reliable.")); level = worst(level, "warning")
    if ch["temperature"] or ch["humidity"] or ch["evaporation"] or ch["wind"] or ch["sunlight"]:
        warnings.append(warn("pet_not_recomputed", "Weather inputs are changed one by one: nothing is derived from another (no physics). This is the model's direct response."))
    checks_used = {}
    for k, code in CHECK_OF.items():
        if ch.get(k) or kind == k:
            c = sm_m["checks"].get(code, {"pass": False}); checks_used[code] = c.get("pass", False)
            if not c.get("pass"):
                warnings.append(warn("experimental", f"The {k} what-if did not pass its check ({code}) with the {sm_m['version']} model: treat it as experimental.")); level = "experimental"
    if ch["evaporation"] or ch["wind"] or ch["sunlight"]:
        warnings.append(warn("experimental", "Changes of evaporation, wind or sunlight have no validation yet.")); level = "experimental"
    if ch["rainfall"] and not ch["drought"] and sm_m["version"] == "v1":
        warnings.append(warn("rain_only", "Rain-only changes failed the sanity checks: the model barely reacts to rain alone and can move the wrong way."))
    if sm_m["version"] == "v3" and (ch["rainfall"] or ch["drought"]):
        warnings.append(warn("era5_rain", "The v3 model reads ERA5-Land's own rain, which is several times wetter than the real rain on this coast; the change is applied to it in the same proportion. Never read it as the real amount of rain."))
    if any(c["within_model_error"] for c in comp):
        warnings.append(warn("within_model_error", "Some differences are smaller than the model's typical error (validation RMSE): they cannot be told apart from noise.",
                             [c["period"] for c in comp if c["within_model_error"]]))

    big = max(comp, key=lambda r: abs(r["absolute_difference"]))
    n_up = sum(r["direction"] == "increased" for r in comp); n_down = sum(r["direction"] == "decreased" for r in comp)
    if not changed:
        summary = "No input was changed: the scenario equals the baseline (a normal year)."
    elif all(r["within_model_error"] for r in comp):
        summary = (f"With these changes the model's median root-zone soil water moves by at most {abs(big['absolute_difference']):.4f} m3/m3 "
                   f"(in {big['period']}), less than its typical error ({rmse:.4f}): the model shows no clear change.")
    else:
        pct = f" ({big['percentage_change']:+.0f} %)" if big["percentage_change"] is not None else ""
        summary = (f"With these changes the model's median root-zone soil water is higher than in a normal year in {n_up} of {horizon} months "
                   f"and lower in {n_down}. The biggest difference is {big['absolute_difference']:+.4f} m3/m3{pct} in {big['period']}.")
    limits = ["A model answer to a made-up situation, not a forecast and not proof of cause and effect.",
              f"Projections beat 'a typical year' only for the first {useful} months (hindcasts 2018-2022).",
              f"In 2023-2025 the 90 % range held the real value {sm_m['coverage']:.0%} of the time: ranges are too narrow in El Niño years.",
              "One 2 km cell; no irrigation in the data; no crop yield."]
    limits = [w_["message"] for w_ in warnings if w_["code"] in ("rain_only", "era5_rain", "experimental", "pet_not_recomputed", "few_analogs", "out_of_domain")] + limits

    res = {
        "simulation_id": sid, "kind": kind, "model_versions": {k: v[:16] for k, v in s.sha.items()} | {"simulations": f"{sm_m['version']} {sm_m['sha256'][:16]}"},
        "location": cell_info(i), "start": start,
        "model": {"algorithm": "XGBoost", "name": sm_m["name"], "version": sm_m["version"], "status": "available", "sha256": sm_m["sha256"]},
        "target": sm_m["card"]["target"] | {"meaning": TARGET_MEANING[sm_m["name"]]},
        "periods": labels,
        "baseline": {"median": _r(bm), "low_90": _r(bl), "high_90": _r(bh), "members": len(w_all["years"]), "analog_years": [int(y) for y in w_all["years"]]},
        "scenario": {"median": _r(am), "low_90": _r(al), "high_90": _r(ah), "members": len(w["years"]), "analog_years": [int(y) for y in w["years"]]},
        "comparison": comp, "ndvi": ndvi, "modified_inputs": changed,
        "out_of_training_range": hard, "unusual_inputs": soft,
        "reliability_level": level, "warnings": warnings,
        "reliability": {"useful_lead_months": useful, "model_rmse_validation": rmse,
                        "range_coverage_2023_2025": sm_m["coverage"],
                        "rain_only_change": ch["rainfall"] and not ch["drought"], "simulation_model": sm_m["version"],
                        "phase2_checks_used": checks_used},
        "interpretation": {"summary": summary, "limitations": list(dict.fromkeys(limits))},
    }
    RESULTS.put(sid, res)
    return res


def _r(a):
    return [round(float(x), 5) for x in a]


def recovery_summary(res: dict, drought_months: int) -> dict:
    """After the dry months: first month back inside the normal-year 90 % range, if it happens within the horizon."""
    back = None
    for k in range(drought_months, len(res["periods"])):
        if res["baseline"]["low_90"][k] <= res["scenario"]["median"][k] <= res["baseline"]["high_90"][k]:
            back = res["periods"][k]; break
    return {"drought_months": drought_months, "back_within_normal_range": back,
            "note": "Recovery of soil water as the model sees it; not recovery of fertility, nutrients or yield."}
