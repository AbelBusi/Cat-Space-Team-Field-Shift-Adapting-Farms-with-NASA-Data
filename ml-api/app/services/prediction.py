"""Predictions: from a full feature set, or for a cell and a period of the observed data cube; history of a cell;
batches; the soil water + NDVI chain of one quarter; the historical error of a place."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import features as FX, state
from .common import GRID_STEP, LRU, PHYSICAL, TARGET_MEANING, make_id, warn, worst
from .common import NotFound, BadRequest

def model_for(variable: str, feats: dict | None = None) -> str:
    """The app's model for a variable: soil water v3 when it is loaded (v1 when the given features are v1's, for older clients)."""
    s = state.get()
    if variable == "ndvi":
        return "ndvi_quarterly"
    if feats is not None and "era5_rain_mm" not in feats:
        return "sm_root_monthly"
    return s.primary["soil_water"]
EXPLAIN_CACHE = LRU(2000)          # prediction_id -> (model name, features) for GET /explanations/{id}


def split_of(year: int) -> str:
    return "training" if year <= 2017 else "validation" if year <= 2022 else "testing"


def find_cell(loc) -> int:
    c = state.get().cube.cells
    cid = loc.cell_id if loc.cell_id is not None else f"{math.floor(loc.lon / GRID_STEP)},{math.floor(loc.lat / GRID_STEP)}"
    hit = np.flatnonzero(c.cell_id.to_numpy() == cid)
    if not len(hit):
        raise NotFound(f"cell {cid} is not in the Lambayeque 2 km grid")
    return int(hit[0])


def find_cell_near(loc, max_km: float = 3.0) -> tuple[int, float]:
    """The cell under a point if it has soil water; otherwise the nearest cell that has it, up to max_km away (a field
    whose centre falls just past the edge of the grid or on a coastal cell). Returns (index, distance in km)."""
    s = state.get(); c = s.cube.cells
    if loc.cell_id is not None:
        return find_cell(loc), 0.0
    has = np.isfinite(s.cube.v["sm_root_m3m3"]).any(axis=1)
    x, y = loc.lon / GRID_STEP, loc.lat / GRID_STEP
    cx, cy = (c.lon.to_numpy() / GRID_STEP), (c.lat.to_numpy() / GRID_STEP)
    d = np.where(has, np.hypot(cx - x, cy - y), np.inf) * GRID_STEP * 111.0     # degrees → km (enough at 7° S)
    i = int(np.argmin(d))
    own = f"{math.floor(loc.lon / GRID_STEP)},{math.floor(loc.lat / GRID_STEP)}"
    if c.cell_id.iloc[i] == own:
        return i, 0.0
    if not np.isfinite(d[i]) or d[i] > max_km:
        raise NotFound("outside_grid: this point is outside the area the models cover (Lambayeque and its edges, 2 km squares)")
    return i, float(d[i])


def find_cell_id(cid: str) -> int:
    return int(np.flatnonzero(state.get().cube.cells.cell_id.to_numpy() == cid)[0])


def cell_info(i: int) -> dict:
    r = state.get().cube.cells.iloc[i]
    return {"cell_id": r.cell_id, "lat": float(r.lat), "lon": float(r.lon), "province": r.province,
            "district": r.district or None, "cell_size_km": 2, "inside_lambayeque": r.province != "outside"}


def outside_warning(i: int) -> list[dict]:
    """Cells of the grid outside Lambayeque (towards Piura, Cajamarca, La Libertad) passed their own validation (S8)."""
    if state.get().cube.cells.province.iloc[i] != "outside":
        return []
    ok = state.check("S8").get("pass")
    return [warn("outside_lambayeque", "This cell is outside Lambayeque. " + ("Its accuracy was checked separately on 2018-2022 (check S8, passed)."
                 if ok else "Its accuracy has not been validated separately (check S8)."))]


def validate_features(name: str, feats: dict) -> list[str]:
    """Exact training names, nothing extra, nothing missing; null only where training had missing values; physical limits."""
    m = state.get().models[name]
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
    if name == "ndvi_quarterly" and "quarter" in feats and feats["quarter"] not in (None, 1, 2, 3, 4):
        problems.append("quarter must be 1, 2, 3 or 4")
    return problems


def _season(name, f):
    if name.startswith("sm_root_monthly"):
        month = round(math.atan2(f["month_sin"], f["month_cos"]) * 6 / math.pi) % 12 or 12
        return "wet Jan-Apr" if month <= 4 else "dry May-Dec"
    return f"Q{int(f['quarter'])}"


def _domain(m, feats) -> tuple[list[str], list[str]]:
    soft = [f for f, b in m["bounds"].items() if feats.get(f) is not None and not (b["p01"] <= feats[f] <= b["p99"])]
    hard = [f for f, b in m["bounds"].items() if feats.get(f) is not None and not (b["min"] <= feats[f] <= b["max"])]
    return soft, hard


def predict_one(name: str, feats: dict, extra: dict | None = None) -> dict:
    """One prediction with its interval, domain warnings, reliability level and an id for /explanations."""
    s = state.get(); m = s.models[name]
    X = pd.DataFrame([{f: (np.nan if feats[f] is None else feats[f]) for f in m["features"]}])[m["features"]]
    pred = float(m["model"].predict(X)[0])
    season = _season(name, feats)
    half = m["intervals"]["half_width_90_by_season"][season]
    soft, hard = _domain(m, feats)
    warnings, level = [], "ok"
    if hard:
        warnings.append(warn("out_of_domain", "Some inputs are outside anything seen in training (1998-2017): the prediction is an extrapolation.", hard))
        level = "out_of_domain"
    elif soft:
        warnings.append(warn("out_of_range", "Some inputs are unusual for training (outside p01-p99): read the prediction with extra care.", soft))
        level = "warning"
    if extra and extra.get("location") and not extra["location"]["inside_lambayeque"]:
        ow = outside_warning(find_cell_id(extra["location"]["cell_id"])); warnings += ow
        if ow and not state.check("S8").get("pass"): level = "experimental"
    if extra and extra.get("split") == "training":
        warnings.append(warn("in_training", "This period was used to train the model: its error here is optimistic."))
        level = worst(level, "warning")
    pid = make_id("pred", {"model": name, "features": feats}, s.sha)
    EXPLAIN_CACHE.put(pid, (name, feats))
    tc = m["intervals"].get("tested_coverage", {})
    return {"prediction_id": pid, "model": name, "target": m["card"]["target"] | {"meaning": TARGET_MEANING[name]}, "prediction": pred,
            "interval_90": {"low": pred - half, "high": pred + half, "nominal": 0.9,
                            "method": f"split conformal, one width per season ({season}), calibrated on 2018-2022",
                            "tested_coverage": tc.get("by_season_90")},
            "out_of_training_range": soft, "far_out_of_training_range": hard,
            "missing_features": [f for f in m["features"] if feats[f] is None],
            "warnings": [w["message"] for w in warnings], "warning_details": warnings, "reliability": level, **(extra or {})}


def _period_index(variable: str, period: str) -> int:
    cube = state.get().cube
    try:
        if variable == "soil_water":
            return cube.t(pd.Timestamp(period + "-01"))
        return int(cube.quarters.get_loc(pd.Period(period, freq="Q")))
    except (KeyError, ValueError):
        span = f"{cube.dates[0]:%Y-%m}..{cube.dates[-1]:%Y-%m}" if variable == "soil_water" else f"{cube.quarters[0]}..{cube.quarters[-1]}"
        raise BadRequest(f"period {period} is not in the data ({span})") from None


def predict_cell(variable: str, loc, period: str) -> dict:
    """Prediction for a cell and month (soil water) or quarter (NDVI), from the observed inputs of the data cube."""
    s = state.get(); i = find_cell(loc); t = _period_index(variable, period)
    name = model_for(variable)
    cols = s.sm_cols if variable == "soil_water" else s.nd_cols
    feats = FX.row(cols, i, t, s.models[name]["features"])
    obs = (s.cube.v["sm_root_m3m3"] if variable == "soil_water" else s.cube.ndvi)[i, t]
    year = int(period[:4])
    problems = [p for p in validate_features(name, feats) if "cannot be null" in p]
    if problems:
        raise NotFound(f"not enough observed data for this cell and period: {problems}")
    return predict_one(name, feats, {"location": cell_info(i), "period": period, "split": split_of(year),
                                     "observed": None if np.isnan(obs) else float(obs)})


def predict_complete(loc, quarter: str) -> dict:
    """The 3 months of soil water of a quarter and the quarter's NDVI, the NDVI fed with the predicted soil water."""
    s = state.get(); i = find_cell(loc); q = pd.Period(quarter, freq="Q"); j = _period_index("ndvi", quarter)
    months = [f"{(q.start_time + pd.DateOffset(months=k)):%Y-%m}" for k in range(3)]
    sm = [predict_cell("soil_water", loc, mth) for mth in months]
    feats = FX.row(s.nd_cols, i, j, s.models["ndvi_quarterly"]["features"])
    feats["q_sm_root_m3m3"] = float(np.mean([r["prediction"] for r in sm]))
    obs = s.cube.ndvi[i, j]
    nd = predict_one("ndvi_quarterly", feats, {"period": quarter, "split": split_of(q.year), "observed": None if np.isnan(obs) else float(obs),
                                                "note": "q_sm_root_m3m3 is the mean of the 3 predicted months, not the observed one"})
    return {"location": cell_info(i), "quarter": quarter, "soil_water": sm, "ndvi": nd,
            "reliability": worst(*[r["reliability"] for r in sm], nd["reliability"])}


def batch(name: str, items: list[dict]) -> dict:
    s = state.get(); m = s.models[name]
    ok, errors = [], []
    for k, it in enumerate(items):
        p = validate_features(name, it)
        (errors.append({"index": k, "detail": p}) if p else ok.append(k))
    results = [None] * len(items)
    if ok:
        X = pd.DataFrame([{f: (np.nan if items[k][f] is None else items[k][f]) for f in m["features"]} for k in ok])[m["features"]]
        preds = m["model"].predict(X)
        for k, pr in zip(ok, preds):
            soft, hard = _domain(m, items[k])
            results[k] = {"index": k, "prediction": float(pr), "reliability": "out_of_domain" if hard else "warning" if soft else "ok",
                          "out_of_training_range": soft}
    return {"model": name, "unit": m["card"]["target"]["unit"], "results": [r for r in results if r], "errors": errors}


def history(variable: str, cell_id: str, start: str | None, end: str | None) -> dict:
    """Observed values and one-step predictions (with the real weather) of a cell, with the period of each row."""
    from ..schemas import Location
    s = state.get(); i = find_cell(Location(cell_id=cell_id))
    if variable == "soil_water":
        labels, obs, pred = [f"{d:%Y-%m}" for d in s.cube.dates], s.cube.v["sm_root_m3m3"][i], s.sm_pred[i]
        halves = [s.models[model_for("soil_water")]["intervals"]["half_width_90_by_season"]["wet Jan-Apr" if d.month <= 4 else "dry May-Dec"] for d in s.cube.dates]
    else:
        labels, obs, pred = [str(q) for q in s.cube.quarters], s.cube.ndvi[i], s.nd_pred[i]
        halves = [s.models["ndvi_quarterly"]["intervals"]["half_width_90_by_season"][f"Q{q.quarter}"] for q in s.cube.quarters]
    rows = []
    for lab, o, p, h in zip(labels, obs, pred, halves):
        if (start and lab < start) or (end and lab > end):
            continue
        rows.append({"period": lab, "observed": None if np.isnan(o) else round(float(o), 5),
                     "predicted": None if np.isnan(p) else round(float(p), 5), "low_90": round(float(p - h), 5), "high_90": round(float(p + h), 5),
                     "split": split_of(int(lab[:4]))})
    return {"location": cell_info(i), "variable": variable, "model": model_for(variable), "unit": s.models[model_for(variable)]["card"]["target"]["unit"],
            "note": "Predicted with each period's real weather (one step). In training years the error is optimistic.", "rows": rows}


def confidence(cell_id: str) -> dict:
    """Historical error of the model at this place (cells sharing the same ERA5-Land pixel), per period. It is not the
    probability that a single prediction is right."""
    from ..schemas import Location
    s = state.get(); i = find_cell(Location(cell_id=cell_id)); c = s.cube.cells
    pix = (c.lat / 0.1).round().astype(int).astype(str) + "," + (c.lon / 0.1).round().astype(int).astype(str)
    grp = np.flatnonzero((pix == pix.iloc[i]).to_numpy())
    yrs = s.cube.dates.year.to_numpy(); obs, pred = s.cube.v["sm_root_m3m3"][grp], s.sm_pred[grp]
    out = {}
    for name, (a, b) in {"validation_2018_2022": (2018, 2022), "testing_2023_2025": (2023, 2025)}.items():
        m = (yrs >= a) & (yrs <= b); e = (pred[:, m] - obs[:, m]).ravel(); e = e[~np.isnan(e)]
        out[name] = {"rmse": float(np.sqrt((e ** 2).mean())) if e.size else None, "bias": float(e.mean()) if e.size else None, "values": int(e.size)}
    chk = state.check("S10")
    return {"location": cell_info(i), "variable": "soil_water", "group": f"{len(grp)} cells sharing one ERA5-Land pixel",
            "historical_error": out, "model": model_for("soil_water"), "model_rmse_validation_all_cells": s.models[model_for("soil_water")]["card"]["metrics"]["validation_2018_2022"]["RMSE"]["value"],
            "reliability": "warning" if chk.get("pass") else "experimental",
            "check_S10": {k: chk.get(k) for k in ("pass", "spearman_val_vs_test_rmse", "status") if k in chk},
            "note": "Past error of the model at this place, not the chance that one prediction is right."}
