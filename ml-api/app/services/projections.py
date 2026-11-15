"""Projections of the whole grid (the "What's ahead" screens), computed once at startup, and one cell's series."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import state
from .common import EL_NINO_YEARS, K, log
from .common import NotFound, BadRequest

DRY_SEASON = [6, 7, 8, 9, 10]               # Jul..Nov when the start is December


def build_bundle(s) -> tuple[dict, dict]:
    """Run the tested models over every Lambayeque cell from the last observed month for the scenarios offered in the
    app: a normal year (all weather years), El Niño years, and two dry months (its global check failed, its mean effect
    dries the soil; see docs/ML_PROJECTIONS.md §4.3). Same code, analog years and range corrections as notebook 06.
    Also returns the drought risk: per cell and lead, the share of analog members below the cell's 20th percentile
    for that calendar month (1998-2017), a feature that is experimental until check S5 passes."""
    import time
    import warnings
    from fs_ml import project as P
    warnings.filterwarnings("ignore", message="(All-NaN slice|Mean of empty slice)")   # cells/quarters with no data stay null
    t0 = time.time()
    cube, sm_m, nd_m = s.cube, s.models["sm_root_monthly"], s.models["ndvi_quarterly"]
    start = cube.dates[-1]
    # the web's projections: cells inside Lambayeque with soil water (the others are served by cell endpoints)
    valid = ~np.isnan(cube.v["sm_root_m3m3"][:, cube.t(start)]) & (cube.cells.province != "outside").to_numpy()
    W = P.analog_weather(cube, start, 12, range(1998, start.year + 1))
    dry_names = [f"{(start + pd.DateOffset(months=k)):%b}" for k in (2, 3)]
    scen = {"base": (W, f"the weather of each past year {W['years'][0]}-{W['years'][-1]}, one by one"),
            "el_nino": (P.select_members(W, EL_NINO_YEARS), f"only coastal El Niño years {EL_NINO_YEARS}"),
            "drought_feb_mar": (P.scenario_drought(W, [2, 3], cube, start), f"no rain and the driest surface soil in {' and '.join(dry_names)}")}
    corr = {v: np.array([s.proj_card["correction_by_lead"][key][str(k)] for k in range(1, n + 1)])
            for v, key, n in (("soil_water", "sm", 12), ("ndvi", "ndvi", 4))}
    out = {"soil_water": {}, "ndvi": {}}
    yrs = cube.dates.year.to_numpy()
    with np.errstate(all="ignore"):
        p20 = {m: np.nanpercentile(cube.v["sm_root_m3m3"][:, (cube.dates.month == m) & (yrs <= 2017)], 20, axis=1) for m in range(1, 13)}
    risk = {}
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
        risk[name] = np.stack([(sm["members"][:, :, k] < p20[d.month][None, :]).mean(axis=0) for k, d in enumerate(sm["dates"])], axis=1)
        risk[name][~valid] = np.nan
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
    return bundle, risk


def projections() -> dict:
    return state.get().bundle


def projection_at(loc, variable: str, scenario: str) -> dict:
    """The series of one cell, in real units (the same numbers as the bundle)."""
    b = state.get().bundle
    if variable not in ("soil_water", "ndvi") or scenario not in b[variable]:
        raise BadRequest("variable must be soil_water or ndvi; scenario one of " + ", ".join(k for k in b["soil_water"] if k != "usual"))
    step = b["meta"]["grid_step_deg"]
    x, y = (math.floor(loc.lon / step), math.floor(loc.lat / step)) if loc.cell_id is None else map(int, loc.cell_id.split(","))
    hit = [i for i, (a, c) in enumerate(zip(b["cells"]["x"], b["cells"]["y"])) if a == x and c == y]
    if not hit:
        raise NotFound("no projection for that point (outside the Lambayeque grid, or a cell without data)")
    i, n = hit[0], len(b["meta"]["periods"][variable])
    get = lambda arr: None if arr is None else [None if v is None else v / K for v in arr[i * n:(i + 1) * n]]
    item = b[variable][scenario]
    return {"cell_id": f"{x},{y}", "variable": variable, "scenario": scenario, "periods": b["meta"]["periods"][variable],
            "median": get(item["median"]), "low_90": get(item.get("low")), "high_90": get(item.get("high")),
            "usual": get(b[variable]["usual"]), "members": item["members"],
            "useful_lead": b["meta"]["useful_lead"]["soil_water_months" if variable == "soil_water" else "ndvi_quarters"]}
