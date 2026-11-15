"""Projections and what-if scenarios with the standard (tested) models. Model level only: no web, no backend.

The tested models describe a month from that month's weather. To look ahead, the weather of the coming months is not
known, so it is taken from past years (an "analog ensemble", the method hydrologists call Ensemble Streamflow
Prediction): starting from the observed state of each cell, the coming months are simulated once with the weather of each
past year, month by month, feeding each predicted soil water value into the next month. The spread of the members is the
weather uncertainty; a correction per lead time, measured on past starts (hindcasts), adds the model error.

A scenario is the same simulation with the weather changed on purpose (e.g. no rain for two months, or only El Niño
years). Scenarios answer "what would the model expect if...", they are not forecasts and are not validated as such.

    cube = build_cube(monthly_panel, quarterly_panel)          # tables built with fs_ml.features
    sm = project_sm(load("sm_root_monthly"), cube, start="2025-12-01", horizon=6, analog_years=range(1998, 2026))
    nd = project_ndvi(load("ndvi_quarterly"), cube, sm)
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .features import SOIL

WEATHER = ["rain_mm", "t2m_c", "pet_mm", "sm_surface_m3m3", "power_rh2m_pct", "power_ws2m_ms", "power_allsky_mj_m2_day"]


@dataclass
class Cube:
    """Every monthly variable as a (cells x months) array, plus the quarterly NDVI as (cells x quarters)."""
    cells: pd.DataFrame                      # cell_id, lat, lon, soil classes (and province / block if present)
    dates: pd.DatetimeIndex                  # consecutive month starts
    v: dict = field(default_factory=dict)    # name -> 2D array
    quarters: pd.PeriodIndex | None = None
    ndvi: np.ndarray | None = None

    def t(self, date) -> int:
        return int(self.dates.get_loc(pd.Timestamp(date)))


def build_cube(monthly: pd.DataFrame, quarterly: pd.DataFrame | None = None) -> Cube:
    """`monthly`: one row per cell and month (fs_ml.features.build_monthly_panel, periods concatenated, no duplicates)."""
    keep = [c for c in ["cell_id", "lat", "lon", *SOIL, "province", "block"] if c in monthly]
    cells = monthly.drop_duplicates("cell_id")[keep].sort_values("cell_id").reset_index(drop=True)
    dates = pd.date_range(monthly.date.min(), monthly.date.max(), freq="MS")
    cube = Cube(cells=cells, dates=dates)
    for col in [*WEATHER, "sm_root_m3m3"]:
        w = monthly.pivot(index="cell_id", columns="date", values=col).reindex(index=cells.cell_id, columns=dates)
        cube.v[col] = w.to_numpy(float)
    if quarterly is not None:
        q = quarterly.assign(p=pd.PeriodIndex.from_fields(year=quarterly.year, quarter=quarterly.quarter, freq="Q"))
        cube.quarters = pd.period_range(q.p.min(), q.p.max(), freq="Q")
        cube.ndvi = q.pivot(index="cell_id", columns="p", values="ndvi").reindex(index=cells.cell_id, columns=cube.quarters).to_numpy(float)
    return cube


def analog_weather(cube: Cube, start: pd.Timestamp, horizon: int, years, until=None) -> dict:
    """Weather of the `horizon` months after `start`, taken from each analog year: member k uses the same calendar
    months of year k (and k+1 when the window crosses December). A member that would need a month after `until` is
    dropped (in hindcasts this keeps the scored years out of the analogs). Returns name -> (members, cells, horizon)."""
    first = pd.Timestamp(start) + pd.DateOffset(months=1)
    out, used = {c: [] for c in WEATHER}, []
    for y in years:
        a = pd.Timestamp(year=int(y), month=first.month, day=1)
        idx = [a + pd.DateOffset(months=k) for k in range(horizon)]
        if idx[0] < cube.dates[0] or idx[-1] > cube.dates[-1] or (until is not None and idx[-1] > pd.Timestamp(until)):
            continue
        ii = [cube.t(d) for d in idx]
        for c in WEATHER:
            out[c].append(cube.v[c][:, ii])
        used.append(int(y))
    if not used:
        raise ValueError("No analog year has the needed months in the cube.")
    w = {c: np.stack(v) for c, v in out.items()}
    w["years"] = np.array(used)
    return w


def _sm_features(m, cube, start_i, w, horizon, sm0, surf0, rain_hist, pet0):
    """Recursive simulation for all members and cells at once. rain_hist: (cells, 5) rain of months t0-4..t0."""
    n_mem, n_cell = w["rain_mm"].shape[:2]
    feats = m["features"]
    soil = {c: np.broadcast_to(cube.cells[c].to_numpy(float), (n_mem, n_cell)) for c in SOIL}
    sm_prev = np.broadcast_to(sm0, (n_mem, n_cell)).copy()
    surf_prev = np.broadcast_to(surf0, (n_mem, n_cell)).copy()
    pet_prev = np.broadcast_to(pet0, (n_mem, n_cell)).copy()
    hist = np.broadcast_to(rain_hist, (n_mem, n_cell, 5)).copy()
    out = np.empty((n_mem, n_cell, horizon))
    for k in range(horizon):
        month = (cube.dates[start_i].month + k) % 12 + 1
        rain = w["rain_mm"][:, :, k]
        cols = {"rain_mm": rain, "rain_mm_lag1": hist[:, :, -1], "rain_mm_lag2": hist[:, :, -2],
                "rain_mm_sum6": hist[:, :, -5:].sum(axis=2) + rain,
                "t2m_c": w["t2m_c"][:, :, k], "pet_mm": w["pet_mm"][:, :, k], "pet_mm_lag1": pet_prev,
                "sm_root_m3m3_lag1": sm_prev, "sm_surface_m3m3_lag1": surf_prev,
                "power_rh2m_pct": w["power_rh2m_pct"][:, :, k], "power_ws2m_ms": w["power_ws2m_ms"][:, :, k],
                "power_allsky_mj_m2_day": w["power_allsky_mj_m2_day"][:, :, k],
                "month_sin": np.full((n_mem, n_cell), np.sin(2 * np.pi * month / 12)),
                "month_cos": np.full((n_mem, n_cell), np.cos(2 * np.pi * month / 12)), **soil}
        X = pd.DataFrame({f: np.asarray(cols[f], float).ravel() for f in feats})
        pred = m["model"].predict(X).reshape(n_mem, n_cell)
        out[:, :, k] = pred
        sm_prev, surf_prev, pet_prev = pred, w["sm_surface_m3m3"][:, :, k], w["pet_mm"][:, :, k]
        hist = np.concatenate([hist[:, :, 1:], rain[:, :, None]], axis=2)
    return out


def project_sm(m: dict, cube: Cube, start, horizon: int, analog_years, weather: dict | None = None, until=None) -> dict:
    """Soil water (28-100 cm) for the `horizon` months after `start` (the last observed month).
    `weather` (from analog_weather, possibly changed by a scenario) overrides the analog years."""
    i = cube.t(start)
    if i < 4:
        raise ValueError("Need 5 months of observed rain before the start.")
    w = weather if weather is not None else analog_weather(cube, start, horizon, analog_years, until)
    sm = _sm_features(m, cube, i, w, horizon, cube.v["sm_root_m3m3"][:, i], cube.v["sm_surface_m3m3"][:, i],
                      cube.v["rain_mm"][:, i - 4:i + 1], cube.v["pet_mm"][:, i])
    dates = pd.date_range(pd.Timestamp(start) + pd.DateOffset(months=1), periods=horizon, freq="MS")
    return {"start": pd.Timestamp(start), "dates": dates, "members": sm, "weather": w, "years": w["years"]}


def project_ndvi(m: dict, cube: Cube, sm_run: dict) -> dict:
    """NDVI of the whole quarters inside a soil water run. The run must start at the end of a quarter
    (Mar, Jun, Sep, Dec). Quarter weather = the analog months; quarter soil water = the simulated values;
    NDVI lags = observed NDVI, then the simulated NDVI of earlier quarters."""
    start = sm_run["start"]
    if start.month % 3 != 0:
        raise ValueError("NDVI projections start at the end of a quarter.")
    w, sm = sm_run["weather"], sm_run["members"]
    n_mem, n_cell, horizon = sm.shape
    nq = horizon // 3
    q0 = pd.Period(start, freq="Q")
    qi = cube.quarters.get_loc(q0)
    ti = cube.t(start)
    obs = cube.ndvi
    feats = m["features"]
    soil = {c: np.broadcast_to(cube.cells[c].to_numpy(float), (n_mem, n_cell)) for c in SOIL}
    # rain of the last observed quarter (for q_rain_mm_lag1 of the first projected quarter)
    prev_rain = np.broadcast_to(cube.v["rain_mm"][:, ti - 2:ti + 1].sum(axis=1), (n_mem, n_cell))
    nd = []
    for j in range(nq):
        s = slice(3 * j, 3 * j + 3)
        q = q0 + j + 1
        lag1 = np.broadcast_to(obs[:, qi], (n_mem, n_cell)) if j == 0 else nd[j - 1]
        lag4 = np.broadcast_to(obs[:, qi + j - 3], (n_mem, n_cell)) if j < 4 else nd[j - 4]
        rain = w["rain_mm"][:, :, s].sum(axis=2)
        cols = {"q_rain_mm": rain, "q_rain_mm_lag1": prev_rain, "q_t2m_c": w["t2m_c"][:, :, s].mean(axis=2),
                "q_pet_mm": w["pet_mm"][:, :, s].sum(axis=2), "q_sm_root_m3m3": sm[:, :, s].mean(axis=2),
                "q_power_rh2m_pct": w["power_rh2m_pct"][:, :, s].mean(axis=2),
                "q_power_ws2m_ms": w["power_ws2m_ms"][:, :, s].mean(axis=2),
                "q_power_allsky_mj_m2_day": w["power_allsky_mj_m2_day"][:, :, s].mean(axis=2),
                "quarter": np.full((n_mem, n_cell), q.quarter, float), "ndvi_lag1": lag1, "ndvi_lag4": lag4, **soil}
        X = pd.DataFrame({f: np.asarray(cols[f], float).ravel() for f in feats})
        nd.append(m["model"].predict(X).reshape(n_mem, n_cell))
        prev_rain = rain
    return {"start": start, "quarters": pd.period_range(q0 + 1, periods=nq, freq="Q"), "members": np.stack(nd, axis=2),
            "years": sm_run["years"]}


# ---------- scenarios: change the analog weather on purpose ----------

def scenario_drought(w: dict, months: list[int], cube: Cube, start, ref_years=(1998, 2017)) -> dict:
    """No rain in the given lead months (1 = first projected month), and the surface soil (0-7 cm) of those months as
    dry as the driest value the cell had in that calendar month in `ref_years` (a dry surface follows a month without
    rain; leaving the analog's wet surface would hide most of the drought)."""
    out = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in w.items()}
    yrs = cube.dates.year
    for k in months:
        month = (pd.Timestamp(start).month + k - 1) % 12 + 1
        cols = (cube.dates.month == month) & (yrs >= ref_years[0]) & (yrs <= ref_years[1])
        driest = np.nanmin(cube.v["sm_surface_m3m3"][:, cols], axis=1)
        out["rain_mm"][:, :, k - 1] = 0.0
        out["sm_surface_m3m3"][:, :, k - 1] = driest[None, :]
    return out


def scenario_rain_factor(w: dict, factor: float, months: list[int] | None = None) -> dict:
    """Rain multiplied by `factor` (0.5 = half the rain, 2 = double) in the given lead months (all if None)."""
    out = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in w.items()}
    idx = range(out["rain_mm"].shape[2]) if months is None else [k - 1 for k in months]
    for k in idx:
        out["rain_mm"][:, :, k] *= factor
    return out


def scenario_adjust(w: dict, rain_factor: float = 1.0, t2m_delta: float = 0.0, rh_delta: float = 0.0,
                    months: list[int] | None = None, pet_factor: float = 1.0, ws_delta: float = 0.0,
                    allsky_delta: float = 0.0) -> dict:
    """The simulator's "buttons": rain × factor, temperature + delta (°C), relative humidity + delta (points, kept in
    0-100), potential evaporation × factor, wind + delta (m/s, ≥ 0), sunlight + delta (MJ/m²/day, ≥ 0), in the given
    lead months (all if None). Only the named inputs change: nothing is derived from another input (no physics), so a
    temperature change shows only the model's direct temperature response. Check `out_of_training_range` first."""
    out = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in w.items()}
    idx = range(out["rain_mm"].shape[2]) if months is None else [k - 1 for k in months]
    for k in idx:
        out["rain_mm"][:, :, k] *= rain_factor
        out["t2m_c"][:, :, k] += t2m_delta
        out["power_rh2m_pct"][:, :, k] = np.clip(out["power_rh2m_pct"][:, :, k] + rh_delta, 0, 100)
        out["pet_mm"][:, :, k] *= pet_factor
        out["power_ws2m_ms"][:, :, k] = np.maximum(out["power_ws2m_ms"][:, :, k] + ws_delta, 0)
        out["power_allsky_mj_m2_day"][:, :, k] = np.maximum(out["power_allsky_mj_m2_day"][:, :, k] + allsky_delta, 0)
    return out


WEATHER_FEATURES = {"rain_mm": "rain_mm", "t2m_c": "t2m_c", "pet_mm": "pet_mm", "power_rh2m_pct": "power_rh2m_pct",
                    "power_ws2m_ms": "power_ws2m_ms", "power_allsky_mj_m2_day": "power_allsky_mj_m2_day"}


def out_of_training_range(w: dict, bounds: dict, soft: bool = False) -> dict:
    """Share of member-cell-months whose weather inputs fall outside the 1998-2017 training range: min-max (the model
    has never seen such weather: an extrapolation) or, with soft=True, p01-p99 (unusual)."""
    lo, hi = ("p01", "p99") if soft else ("min", "max")
    out = {}
    for k, f in WEATHER_FEATURES.items():
        if f in bounds and k in w:
            v = w[k]
            out[k] = float(((v < bounds[f][lo]) | (v > bounds[f][hi])).mean())
    return out


def select_members(w: dict, years) -> dict:
    """Keep only some analog years (e.g. El Niño years)."""
    keep = np.isin(w["years"], list(years))
    if not keep.any():
        raise ValueError("None of those years is in the ensemble.")
    return {k: (v[keep] if isinstance(v, np.ndarray) and v.ndim >= 1 and len(v) == len(keep) else v) for k, v in w.items()}


# ---------- summaries ----------

def summarize(members: np.ndarray, correction: np.ndarray | None = None, q=(0.05, 0.5, 0.95)) -> dict:
    """Median and band of the members per cell and lead. `correction` (per lead) widens the band by the model error
    measured on hindcasts (conformalized band)."""
    lo, med, hi = np.quantile(members, q, axis=0)
    if correction is not None:
        lo, hi = lo - correction[None, :], hi + correction[None, :]
    return {"low": lo, "median": med, "high": hi}
