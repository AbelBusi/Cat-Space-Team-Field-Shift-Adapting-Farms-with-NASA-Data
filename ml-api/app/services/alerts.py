"""Alerts: cells whose observed value fell below the lower end of the 90 % band projected one step earlier.

The band comes from the analog ensemble (every past year's weather except the year being checked) plus the conformal
correction of lead 1. With a calibrated band about 5 % of cells are flagged by chance in a normal month (check S6).
The data cube ends in 2025-12 and is updated by hand, so alerts are for past months until a monthly ingest exists."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import state
from .analysis import _by_district
from .common import LRU
from .common import BadRequest

CACHE = LRU(64)


def _flag(lo, obs, kind, label):
    s = state.get(); c = s.cube.cells
    ok = np.isfinite(obs) & np.isfinite(lo)
    flag = ok & (obs < lo)
    chk = state.check("S6")
    return {"kind": kind, "period": label, "cells_checked": int(ok.sum()), "cells_flagged": int(flag.sum()),
            "share_flagged": float(flag.sum() / max(1, ok.sum())), "expected_by_chance": 0.05,
            "districts": _by_district(np.where(ok, flag.astype(float), np.nan)),
            "cells": [{"cell_id": c.cell_id.iloc[i], "district": c.district.iloc[i] or None, "observed": round(float(obs[i]), 4),
                       "lower_90": round(float(lo[i]), 4)} for i in np.flatnonzero(flag)[:500]],
            "reliability": "warning" if chk.get("pass") else "experimental",
            "check_S6": {k: chk.get(k) for k in ("pass", "flag_share_soil_water", "flag_share_ndvi") if k in chk},
            "note": "District values are the share of their cells flagged. A flag says 'drier or less green than the model expected', not a diagnosis."}


def drought(month: str) -> dict:
    from fs_ml import project as P
    if (hit := CACHE.get(("sm", month))): return hit
    s = state.get(); cube = s.cube
    t = pd.Timestamp(month + "-01")
    if t not in cube.dates or cube.t(t) < 6:
        raise BadRequest(f"month must be between {cube.dates[6]:%Y-%m} and {cube.dates[-1]:%Y-%m}")
    start = t - pd.DateOffset(months=1)
    years = [y for y in range(1998, cube.dates[-1].year + 1) if y != t.year]
    run = P.project_sm(s.models["sm_root_monthly"], cube, start, 1, years)
    lo = np.quantile(run["members"][:, :, 0], 0.05, axis=0) - s.proj_card["correction_by_lead"]["sm"]["1"]
    out = _flag(lo, cube.v["sm_root_m3m3"][:, cube.t(t)], "soil_water_below_expected", month)
    CACHE.put(("sm", month), out)
    return out


def vegetation(quarter: str) -> dict:
    from fs_ml import project as P
    if (hit := CACHE.get(("nd", quarter))): return hit
    s = state.get(); cube = s.cube
    q = pd.Period(quarter, freq="Q")
    if q not in cube.quarters or cube.quarters.get_loc(q) < 2:
        raise BadRequest(f"quarter must be between {cube.quarters[2]} and {cube.quarters[-1]}")
    start = (q - 1).to_timestamp(how="end").normalize().replace(day=1)
    years = [y for y in range(1998, cube.dates[-1].year + 1) if y != q.year]
    sm = P.project_sm(s.models["sm_root_monthly"], cube, start, 3, years)
    nd = P.project_ndvi(s.models["ndvi_quarterly"], cube, sm)
    lo = np.quantile(nd["members"][:, :, 0], 0.05, axis=0) - s.proj_card["correction_by_lead"]["ndvi"]["1"]
    out = _flag(lo, cube.ndvi[:, cube.quarters.get_loc(q)], "ndvi_below_expected", quarter)
    CACHE.put(("nd", quarter), out)
    return out
