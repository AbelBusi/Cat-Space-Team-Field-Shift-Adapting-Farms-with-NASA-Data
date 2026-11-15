"""Territorial analysis: districts, rankings, drought risk, anomalies and hotspots.

Districts come from the data cube: each 2 km cell carries the province and district of the OpenStreetMap boundaries the
web app uses (ODbL). A district value is the **median of its cells** with the number of cells next to it; districts
with fewer than 3 cells get a warning, districts without cells are not reported (nothing is invented)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import state
from .common import K, warn
from .common import BadRequest

MIN_CELLS = 3


def _by_district(values: np.ndarray, province: str | None = None, mask: np.ndarray | None = None) -> list[dict]:
    s = state.get(); c = s.cube.cells
    keep = (c.district != "").to_numpy() & ~np.isnan(values)
    if mask is not None: keep &= mask
    if province: keep &= (c.province == province).to_numpy()
    df = pd.DataFrame({"district": c.district[keep].to_numpy(), "province": c.province[keep].to_numpy(), "v": values[keep]})
    g = df.groupby(["district", "province"]).v.agg(["median", "size"]).reset_index()
    return [{"district": r.district, "province": r.province, "cells": int(r["size"]), "value": round(float(r["median"]), 4),
             **({"warning": f"only {int(r['size'])} cells"} if r["size"] < MIN_CELLS else {})} for _, r in g.iterrows()]


def districts(province: str | None = None) -> dict:
    s = state.get(); cube = s.cube
    last_nd = max(j for j in range(cube.ndvi.shape[1]) if np.isfinite(cube.ndvi[:, j]).any())
    sm = _by_district(cube.v["sm_root_m3m3"][:, -1], province)
    nd = {(r["district"]): r for r in _by_district(cube.ndvi[:, last_nd], province)}
    summ = {r["district"]: r for r in s.bundle["district_summary"] if r["scenario"] == "base"}
    rows = []
    for r in sm:
        d = r["district"]
        rows.append({"district": d, "province": r["province"], "cells": r["cells"],
                     "observed_soil_water_last_month": r["value"], "observed_ndvi_last_quarter": nd.get(d, {}).get("value"),
                     "projected_dry_season_soil_water": summ[d]["dry_season_soil_water"] / K if d in summ else None,
                     **({"warning": r["warning"]} if "warning" in r else {})})
    return {"last_month": f"{cube.dates[-1]:%Y-%m}", "last_quarter_with_ndvi": str(cube.quarters[last_nd]),
            "projection_start": s.bundle["meta"]["start"], "aggregation": "median of the district's 2 km cells", "districts": rows,
            "source": "district and province of each cell: OpenStreetMap boundaries (ODbL)"}


def ranking(metric: str, scenario: str, province: str | None) -> dict:
    s = state.get(); key = {"water-retention": "dry_season_soil_water", "vegetation": "q3q4_ndvi"}[metric]
    rows = [r for r in s.bundle["district_summary"] if r["scenario"] == scenario and r[key] is not None]
    if not rows:
        raise BadRequest(f"unknown scenario {scenario}; one of " + ", ".join(sorted({r['scenario'] for r in s.bundle['district_summary']})))
    if province:
        prov = dict(zip(s.cube.cells.district, s.cube.cells.province))
        rows = [r for r in rows if prov.get(r["district"]) == province]
    rows = sorted(rows, key=lambda r: -r[key])
    p = s.bundle["meta"]["periods"]
    warnings = [warn("beyond_useful_lead", "Jul-Nov is beyond the 6-month useful lead: closer to a typical year than a forecast.")] if metric == "water-retention" else []
    return {"metric": metric, "scenario": scenario, "unit": "m3/m3" if metric == "water-retention" else "NDVI",
            "period": f"{p['soil_water'][6]}..{p['soil_water'][10]}" if metric == "water-retention" else f"{p['ndvi'][2]}..{p['ndvi'][3]}",
            "aggregation": "median of the district's 2 km cells",
            "districts": [{"rank": k + 1, "district": r["district"], "cells": r["cells"], "value": r[key] / K,
                           **({"warning": f"only {r['cells']} cells"} if r["cells"] < MIN_CELLS else {})} for k, r in enumerate(rows)],
            "warnings": warnings + [warn("not_harvest", "More water in the soil is not a better harvest: crop, irrigation and market decide.")],
            "reliability": "warning"}


def drought_risk(scenario: str, lead: int, province: str | None) -> dict:
    s = state.get()
    if scenario not in s.risk:
        raise BadRequest(f"scenario must be one of {sorted(s.risk)}")
    if not 1 <= lead <= s.risk[scenario].shape[1]:
        raise BadRequest("lead must be between 1 and 12")
    chk = state.check("S5")
    period = s.bundle["meta"]["periods"]["soil_water"][lead - 1]
    return {"scenario": scenario, "period": period, "lead": lead,
            "definition": "share of the analog weather years in which the model puts the cell's soil water below its 20th percentile for that month (1998-2017)",
            "districts": _by_district(s.risk[scenario][:, lead - 1], province),
            "reliability": "warning" if chk.get("pass") else "experimental",
            "check_S5": {k: chk.get(k) for k in ("pass", "brier_skill", "max_gap", "status") if k in chk},
            "note": "Not an official drought probability; it counts how many past years' weather lead to a dry soil in the model."}


def _residuals(variable: str) -> tuple[np.ndarray, list[str], float]:
    s = state.get()
    if variable == "soil_water":
        return s.cube.v["sm_root_m3m3"] - s.sm_pred, [f"{d:%Y-%m}" for d in s.cube.dates], s.models["sm_root_monthly"]["card"]["metrics"]["validation_2018_2022"]["RMSE"]["value"]
    return s.cube.ndvi - s.nd_pred, [str(q) for q in s.cube.quarters], s.models["ndvi_quarterly"]["card"]["metrics"]["validation_2018_2022"]["RMSE"]["value"]


def anomalies(variable: str, period: str, province: str | None) -> dict:
    """Observed minus predicted (with the real weather), in units of the model's validation RMSE."""
    res, labels, err = _residuals(variable)
    if period not in labels:
        raise BadRequest(f"period must be one of {labels[0]}..{labels[-1]}")
    z = res[:, labels.index(period)] / err
    s = state.get(); c = s.cube.cells
    ok = np.isfinite(z)
    top = np.argsort(-np.abs(np.where(ok, z, 0)))[:20]
    chk = state.check("S7") if variable == "ndvi" else {"pass": True}
    return {"variable": variable, "period": period, "unit": "times the model error (validation RMSE)", "model_error": err,
            "share_of_cells_beyond_2": float((np.abs(z[ok]) > 2).mean()) if ok.any() else None,
            "districts": _by_district(z, province),
            "strongest_cells": [{"cell_id": c.cell_id.iloc[i], "district": c.district.iloc[i] or None, "z": round(float(z[i]), 2)} for i in top if ok[i]],
            "reliability": "experimental" if variable == "ndvi" and not chk.get("pass") else "warning",
            "note": ("NDVI greener than expected may come from irrigation, a crop change, natural vegetation after rain or "
                     "errors of the composite: it does not prove irrigation (check S7: not testable without irrigated-area data).")
            if variable == "ndvi" else "Soil water different from what the model expects with that month's weather."}


def hotspots(since: str, min_quarters: int, province: str | None) -> dict:
    """Cells where NDVI was above the model's expectation by more than its error in at least `min_quarters` quarters
    since `since`, with at least 2 such neighbours (a patch, not a lone cell)."""
    res, labels, err = _residuals("ndvi")
    if since not in labels:
        raise BadRequest(f"since must be one of {labels[0]}..{labels[-1]}")
    cnt = (res[:, labels.index(since):] > err).sum(axis=1)
    hot = cnt >= min_quarters
    s = state.get(); c = s.cube.cells
    xy = c.cell_id.str.split(",", expand=True).astype(int).to_numpy(); hot_set = {tuple(p) for p in xy[hot]}
    patch = np.array([h and sum((x + dx, y + dy) in hot_set for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy) >= 2
                      for h, (x, y) in zip(hot, xy)])
    if province: patch &= (c.province == province).to_numpy()
    by_d = pd.Series(c.district[patch].replace("", "(no district)")).value_counts().to_dict()
    return {"variable": "ndvi", "since": since, "min_quarters": min_quarters, "cells": int(patch.sum()),
            "by_district": by_d, "cell_ids": c.cell_id[patch].tolist()[:500],
            "reliability": "experimental",
            "note": "Greener than the weather explains, persistently and in patches. Possibly irrigation, but not proof: validate with irrigated-area data first."}
