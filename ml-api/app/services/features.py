"""Model inputs for every cell and month (or quarter) from the observed data cube, built exactly like
ml/fs_ml/features.py builds the training tables (same lags, same 6-month sum, same quarterly sums and means).
A test checks that a row built here gives the same prediction as fs_ml.project with the real weather."""
from __future__ import annotations

import numpy as np

from fs_ml.features import SOIL


def _shift(a: np.ndarray, k: int) -> np.ndarray:
    out = np.full_like(a, np.nan)
    out[:, k:] = a[:, :-k]
    return out


def _sum6(rain: np.ndarray) -> np.ndarray:
    out = np.full_like(rain, np.nan)
    for t in range(5, rain.shape[1]):
        out[:, t] = rain[:, t - 5:t + 1].sum(axis=1)           # NaN if any month missing (min_periods=6)
    return out


def sm_matrix(cube) -> dict:
    """name -> (cells, months) array of every soil water feature (v1, plus the ERA5-Land rain ones of v3 when the cube has it)."""
    v = cube.v
    rain = v["rain_mm"]
    month = np.broadcast_to(cube.dates.month.to_numpy(), rain.shape)
    n = rain.shape
    cols = {"rain_mm": rain, "rain_mm_lag1": _shift(rain, 1), "rain_mm_lag2": _shift(rain, 2), "rain_mm_sum6": _sum6(rain),
            "t2m_c": v["t2m_c"], "pet_mm": v["pet_mm"], "pet_mm_lag1": _shift(v["pet_mm"], 1),
            "sm_root_m3m3_lag1": _shift(v["sm_root_m3m3"], 1), "sm_surface_m3m3_lag1": _shift(v["sm_surface_m3m3"], 1),
            "power_rh2m_pct": v["power_rh2m_pct"], "power_ws2m_ms": v["power_ws2m_ms"],
            "power_allsky_mj_m2_day": v["power_allsky_mj_m2_day"],
            "month_sin": np.sin(2 * np.pi * month / 12), "month_cos": np.cos(2 * np.pi * month / 12)}
    if "era5_rain_mm" in v:
        e = v["era5_rain_mm"]
        cols |= {"era5_rain_mm": e, "era5_rain_mm_lag1": _shift(e, 1), "era5_rain_mm_lag2": _shift(e, 2), "era5_rain_mm_sum6": _sum6(e)}
    for c in SOIL:
        cols[c] = np.broadcast_to(cube.cells[c].to_numpy(float)[:, None], n)
    return cols


def nd_matrix(cube) -> dict:
    """name -> (cells, quarters) array of every NDVI feature. The cube starts in January, so quarter j = months 3j..3j+2."""
    v, nq = cube.v, len(cube.quarters)
    qs = lambda a: a[:, :3 * nq].reshape(a.shape[0], nq, 3)
    with np.errstate(all="ignore"):
        q_sum = lambda a: qs(a).sum(axis=2)                        # NaN if any month is missing (as in training)
        q_mean = lambda a: np.nanmean(qs(a), axis=2)               # pandas mean skips missing months
        cols = {"q_rain_mm": q_sum(v["rain_mm"]), "q_t2m_c": q_mean(v["t2m_c"]), "q_pet_mm": q_sum(v["pet_mm"]),
                "q_sm_root_m3m3": q_mean(v["sm_root_m3m3"]), "q_power_rh2m_pct": q_mean(v["power_rh2m_pct"]),
                "q_power_ws2m_ms": q_mean(v["power_ws2m_ms"]), "q_power_allsky_mj_m2_day": q_mean(v["power_allsky_mj_m2_day"])}
    cols["q_rain_mm_lag1"] = _shift(cols["q_rain_mm"], 1)
    cols["quarter"] = np.broadcast_to(np.array([q.quarter for q in cube.quarters], float), cube.ndvi.shape)
    cols["ndvi_lag1"], cols["ndvi_lag4"] = _shift(cube.ndvi, 1), _shift(cube.ndvi, 4)
    for c in SOIL:
        cols[c] = np.broadcast_to(cube.cells[c].to_numpy(float)[:, None], cube.ndvi.shape)
    return cols


def predict_matrix(model: dict, cols: dict) -> np.ndarray:
    """One-step predictions for every (cell, period), shape (cells, periods)."""
    import pandas as pd
    shape = next(iter(cols.values())).shape
    X = pd.DataFrame({f: np.asarray(cols[f], float).ravel() for f in model["features"]})
    return model["model"].predict(X).reshape(shape)


def row(cols: dict, i: int, t: int, features: list[str]) -> dict:
    """The feature dict of one cell and period (None where missing)."""
    out = {}
    for f in features:
        x = float(cols[f][i, t])
        out[f] = None if np.isnan(x) else x
    return out
