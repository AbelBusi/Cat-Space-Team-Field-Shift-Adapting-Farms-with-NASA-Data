"""Trends of yearly values (docs/ML_TRENDS.md): Theil-Sen slope with Sen's 95 % interval, and the extension of a trend
with its year-to-year range. Numpy only, used by ml/scripts/trend_check.py and by the ML API."""
from __future__ import annotations

import math
import warnings

import numpy as np

Z95 = 1.959963984540054

# variable -> (cube key, how the year is built, minimum periods per year)
VARIABLES = {"soil_water": ("sm_root_m3m3", "mean", 12), "temperature": ("t2m_c", "mean", 12),
             "rain": ("rain_mm", "sum", 12), "ndvi": ("ndvi", "mean", 3)}


def yearly(values: np.ndarray, years: np.ndarray, how: str, need: int) -> tuple[np.ndarray, np.ndarray]:
    """(cells, periods) -> (year list, (cells, years)) with NaN where a year has fewer than `need` values."""
    ys = np.unique(years)
    out = np.full((values.shape[0], len(ys)), np.nan)
    for j, y in enumerate(ys):
        v = values[:, years == y]
        n = np.isfinite(v).sum(axis=1)
        with np.errstate(all="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)          # years without data stay NaN
            agg = np.nansum(v, axis=1) if how == "sum" else np.nanmean(v, axis=1)
        out[:, j] = np.where(n >= need, agg, np.nan)
    return ys, out


def theil_sen(x: np.ndarray, y: np.ndarray) -> dict | None:
    """Median of pairwise slopes, intercept by the median of y - slope x, and Sen's 95 % interval of the slope."""
    ok = np.isfinite(y)
    x, y = np.asarray(x, float)[ok], np.asarray(y, float)[ok]
    n = len(x)
    if n < 8:
        return None
    i, j = np.triu_indices(n, 1)
    dx = x[j] - x[i]
    s = np.sort((y[j] - y[i])[dx != 0] / dx[dx != 0])
    slope = float(np.median(s))
    # Kendall's S variance without ties in x (one value per year); Sen (1968) interval
    c = Z95 * math.sqrt(n * (n - 1) * (2 * n + 5) / 18)
    m = len(s)
    lo_k, hi_k = int(round((m - c) / 2)), int(round((m + c) / 2)) + 1
    lo = float(s[max(0, lo_k - 1)]); hi = float(s[min(m - 1, hi_k - 1)])
    intercept = float(np.median(y - slope * x))
    resid = y - (intercept + slope * x)
    return {"slope": slope, "slope_low": lo, "slope_high": hi, "intercept": intercept, "n_years": n,
            "clear": bool(lo > 0 or hi < 0), "resid_p05": float(np.quantile(resid, 0.05)), "resid_p95": float(np.quantile(resid, 0.95)),
            "x_mean": float(x.mean())}


def extend(t: dict, years) -> dict:
    """Centre and range of the trend at future years: the line ± the detrended 5-95 % range ± the slope's spread."""
    years = np.asarray(years, float)
    centre = t["intercept"] + t["slope"] * years
    spread = np.abs(years - t["x_mean"]) * (t["slope_high"] - t["slope_low"]) / 2
    return {"years": years.astype(int).tolist(), "centre": centre.tolist(),
            "low": (centre + t["resid_p05"] - spread).tolist(), "high": (centre + t["resid_p95"] + spread).tolist()}
