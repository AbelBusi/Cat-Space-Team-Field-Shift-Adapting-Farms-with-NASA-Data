"""The "History" mode of the web: the whole department since 1998, and the facts its chapters tell. Everything is
computed from the cube and the trends (docs/ML_TRENDS.md); no sentence of the web carries a number typed by hand."""
from __future__ import annotations

import base64

import numpy as np

from . import state
from .common import EL_NINO_YEARS

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def _district_medians(values: np.ndarray, districts: np.ndarray, least: int = 5) -> list[tuple[str, float, int]]:
    out = []
    for d in sorted(set(districts) - {""}):
        v = values[(districts == d) & np.isfinite(values)]
        if len(v) >= least:
            out.append((d, float(np.median(v)), int(len(v))))
    return out


def build() -> dict:
    s = state.get(); cube = s.cube; c = cube.cells
    root = cube.v["sm_root_m3m3"]
    inside = ((c.province != "outside") & np.isfinite(root).any(axis=1)).to_numpy()
    idx = np.flatnonzero(inside)
    R = root[idx]                                                    # (cells, months)
    lo, hi = np.nanpercentile(R, [2, 98])
    scaled = np.clip((R - lo) / (hi - lo), 0, 1)
    packed = np.where(np.isfinite(scaled), np.round(scaled * 254) + 1, 0).astype(np.uint8)   # 0 = no value
    xy = c.cell_id.iloc[idx].str.split(",", expand=True).astype(int)
    months = cube.dates.month.to_numpy(); years = cube.dates.year.to_numpy()
    dept = np.nanmean(R, axis=0)
    usual = np.array([dept[months == m].mean() for m in range(1, 13)])
    anom = dept - usual[months - 1]

    k = int(np.argmax(dept))
    wettest = {"month": MONTHS[months[k] - 1], "year": int(years[k]), "index": k, "value": round(float(dept[k]), 4),
               "usual": round(float(usual[months[k] - 1]), 4), "percent_over_usual": round(float((dept[k] / usual[months[k] - 1] - 1) * 100), 1)}
    peaks = []
    for i in np.argsort(-anom):
        if all(abs(int(years[i]) - p["year"]) > 1 for p in peaks):
            peaks.append({"month": MONTHS[months[i] - 1], "year": int(years[i]), "index": int(i), "anomaly": round(float(anom[i]), 4),
                          "el_nino_year": int(years[i]) in EL_NINO_YEARS})
        if len(peaks) == 3:
            break
    ys = np.unique(years)
    annual = np.array([dept[years == y].mean() for y in ys])
    wet_season = np.isin(months, [2, 3, 4]); nino = np.isin(years, EL_NINO_YEARS)

    tr = s.trends
    def shares(name):
        fits = [tr[name]["fits"][i] for i in idx]
        ok = [f for f in fits if f]
        slope = np.array([np.nan if f is None else f["slope"] * 10 for f in fits])
        return {"cells": len(ok), "clear_up": round(sum(f["clear"] and f["slope"] > 0 for f in ok) / max(1, len(ok)), 3),
                "clear_down": round(sum(f["clear"] and f["slope"] < 0 for f in ok) / max(1, len(ok)), 3),
                "median_per_decade": round(float(np.nanmedian(slope)), 4)}, slope
    districts = c.district.iloc[idx].to_numpy()
    temp, t_slope = shares("temperature"); green, g_slope = shares("ndvi"); soil, s_slope = shares("soil_water"); rain, _ = shares("rain")
    g_d = sorted(_district_medians(g_slope, districts), key=lambda r: -r[1])
    s_d = sorted(_district_medians(s_slope, districts), key=lambda r: r[1])
    named = lambda r: {"district": r[0], "per_decade": round(r[1], 4), "cells": r[2]}
    return {
        "cells": {"x": xy[0].tolist(), "y": xy[1].tolist()},
        "months": [f"{d:%Y-%m}" for d in cube.dates],
        "soil_water": {"packed_base64": base64.b64encode(packed.tobytes()).decode(), "order": "cell by cell, months inside; 0 = no value, 1-255 = low to high",
                       "low": round(float(lo), 4), "high": round(float(hi), 4), "unit": "m3/m3"},
        "department_mean": [round(float(v), 4) for v in dept],
        "el_nino_years": EL_NINO_YEARS,
        "trend_per_decade": {"temperature": [None if not np.isfinite(v) else round(float(v), 3) for v in t_slope],
                             "ndvi": [None if not np.isfinite(v) else round(float(v), 4) for v in g_slope],
                             "soil_water": [None if not np.isfinite(v) else round(float(v), 5) for v in s_slope]},
        "insights": {
            "span": {"first": int(ys[0]), "last": int(ys[-1]), "cells": int(len(idx)), "months": int(R.shape[1])},
            "wettest_month": wettest, "wet_peaks": peaks,
            "driest_year": {"year": int(ys[int(np.argmin(annual))]), "value": round(float(annual.min()), 4)},
            "wettest_year": {"year": int(ys[int(np.argmax(annual))]), "value": round(float(annual.max()), 4)},
            "el_nino_wet_season": {"anomaly_el_nino_years": round(float(anom[wet_season & nino].mean()), 4),
                                   "anomaly_other_years": round(float(anom[wet_season & ~nino].mean()), 4), "months": "February-April"},
            "warming": temp, "greening": green | {"top_districts": [named(r) for r in g_d[:3]]},
            "soil_water": soil | {"drying_most": [named(r) for r in s_d[:3]], "wetting_most": [named(r) for r in s_d[-1:-3:-1]]},
            "rain": rain,
        },
        "notes": ["Soil water is ERA5-Land (about 9 km) read on 2 km squares: neighbours often share a value, and irrigation is not in it.",
                  "A trend is called clear only if its 95 % interval excludes zero (docs/ML_TRENDS.md).",
                  "These are descriptions of 1998-2025, not causes and not forecasts."],
    }


def history() -> dict:
    s = state.get()
    if "history" not in s.cache:
        s.cache["history"] = build()
    return s.cache["history"]
