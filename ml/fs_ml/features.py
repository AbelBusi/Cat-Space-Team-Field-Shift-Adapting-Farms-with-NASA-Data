"""Model tables: static cell attributes, the monthly panel and the quarterly panel, plus the exact feature lists.

Lags are always taken inside one cell and by calendar position, so a lag never crosses into another cell and a gap
stays a gap (NaN). Only past or same-period values are used as features; the target itself is never shifted forward.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

# FAO GAEZ layers used as static features. Left out: the "Low" copies of lime/gypsum, salinity/sodicity and rooting
# (identical, pixel by pixel, to the "High" files) and Oxygen Availability High (one value, 10, in all of Lambayeque).
GAEZ_FEATURES = {
    "gaez_nutrient_low": "soil_nutrient_low_class",
    "gaez_oxygen_low": "soil_oxygen_low_class",
    "gaez_lime_gypsum_high": "soil_lime_gypsum_class",
    "gaez_salinity_high": "soil_salinity_sodicity_class",
    "gaez_rooting_high": "soil_rooting_class",
}
SOIL = list(GAEZ_FEATURES.values())

# Target 1: root-zone soil water of month t (ERA5-Land layer 3, 28-100 cm) from the weather of month t, the months
# before it, and the soil state of month t-1.
SM_TARGET = "sm_root_m3m3"
SM_FEATURES = [
    "rain_mm", "rain_mm_lag1", "rain_mm_lag2", "rain_mm_sum6",
    "t2m_c", "pet_mm", "pet_mm_lag1",
    "sm_root_m3m3_lag1", "sm_surface_m3m3_lag1",
    "power_rh2m_pct", "power_ws2m_ms", "power_allsky_mj_m2_day",
    "month_sin", "month_cos",
    *SOIL,
]

# Target 2: NDVI of quarter q from the weather of quarter q, the quarter before it, and the NDVI seen 1 and 4 quarters
# earlier (NaN when that quarter has no image).
NDVI_TARGET = "ndvi"
NDVI_FEATURES = [
    "q_rain_mm", "q_rain_mm_lag1", "q_t2m_c", "q_pet_mm", "q_sm_root_m3m3",
    "q_power_rh2m_pct", "q_power_ws2m_ms", "q_power_allsky_mj_m2_day",
    "quarter", "ndvi_lag1", "ndvi_lag4",
    *SOIL,
]

# Kept in the tables to split and group rows, never used as features (the model must learn from conditions, not
# memorize places or years).
ID_COLUMNS = ["cell_id", "date", "year", "month", "quarter_id", "lat", "lon"]


def nearest(points: pd.DataFrame, lat: str, lon: str, cells: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Index of the nearest point for every cell center, and the distance in degrees."""
    dist, idx = cKDTree(points[[lat, lon]].to_numpy()).query(cells[["lat", "lon"]].to_numpy(), k=1)
    return idx, dist


def static_cells(cells: pd.DataFrame, gaez: dict[str, pd.DataFrame], power_grid: pd.DataFrame,
                 ceres_grid: pd.DataFrame) -> pd.DataFrame:
    """Per cell: the 5 GAEZ classes of the nearest GAEZ pixel, and the NASA POWER grid points to read climate from."""
    out = cells.copy()
    for key, col in GAEZ_FEATURES.items():
        idx, dist = nearest(gaez[key], "latitude", "longitude", out)
        out[col] = gaez[key]["value"].to_numpy()[idx]
        out[f"{col}_dist_deg"] = dist
    idx, dist = nearest(power_grid, "power_lat", "power_lon", out)
    out["merra_lat"], out["merra_lon"] = power_grid["power_lat"].to_numpy()[idx], power_grid["power_lon"].to_numpy()[idx]
    out["merra_dist_deg"] = dist
    idx, dist = nearest(ceres_grid, "power_lat", "power_lon", out)
    out["ceres_lat"], out["ceres_lon"] = ceres_grid["power_lat"].to_numpy()[idx], ceres_grid["power_lon"].to_numpy()[idx]
    out["ceres_dist_deg"] = dist
    return out


def build_monthly_panel(monthly: pd.DataFrame, cells: pd.DataFrame, merra: pd.DataFrame,
                        ceres: pd.DataFrame) -> pd.DataFrame:
    """One row per cell and month with the features of SM_FEATURES. `merra` holds RH2M, WS2M (and T2M) on the
    0.5° x 0.625° grid, `ceres` holds ALLSKY_SFC_SW_DWN on the 1° grid."""
    df = monthly.merge(cells, on="cell_id", how="left", validate="many_to_one")
    df = df.merge(merra.rename(columns={"power_lat": "merra_lat", "power_lon": "merra_lon"}),
                  on=["merra_lat", "merra_lon", "date"], how="left", validate="many_to_one")
    df = df.merge(ceres.rename(columns={"power_lat": "ceres_lat", "power_lon": "ceres_lon"}),
                  on=["ceres_lat", "ceres_lon", "date"], how="left", validate="many_to_one")
    df = df.sort_values(["cell_id", "date"]).reset_index(drop=True)
    df["year"], df["month"] = df["date"].dt.year, df["date"].dt.month

    step = df.groupby("cell_id")["date"].diff().dt.days
    if not step.dropna().between(28, 31).all():
        raise ValueError("A cell has a gap or a repeated month: lags would be wrong.")
    g = df.groupby("cell_id", sort=False)
    df["rain_mm_lag1"] = g["rain_mm"].shift(1)
    df["rain_mm_lag2"] = g["rain_mm"].shift(2)
    df["rain_mm_sum6"] = g["rain_mm"].transform(lambda s: s.rolling(6, min_periods=6).sum())
    df["pet_mm_lag1"] = g["pet_mm"].shift(1)
    df["sm_root_m3m3_lag1"] = g["sm_root_m3m3"].shift(1)
    df["sm_surface_m3m3_lag1"] = g["sm_surface_m3m3"].shift(1)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    return df


def build_quarterly_panel(monthly_panel: pd.DataFrame, veg: pd.DataFrame) -> pd.DataFrame:
    """One row per cell and quarter: climate of the quarter (sums for rain and evaporation, means for the rest),
    NDVI of the quarter (target, NaN when there is no image) and the NDVI lags."""
    m = monthly_panel.assign(quarter=(monthly_panel["month"] - 1) // 3 + 1)
    agg = m.groupby(["cell_id", "year", "quarter"]).agg(
        n_months=("date", "size"),
        q_rain_mm=("rain_mm", "sum"), q_pet_mm=("pet_mm", "sum"),
        q_t2m_c=("t2m_c", "mean"), q_sm_root_m3m3=("sm_root_m3m3", "mean"),
        q_power_rh2m_pct=("power_rh2m_pct", "mean"), q_power_ws2m_ms=("power_ws2m_ms", "mean"),
        q_power_allsky_mj_m2_day=("power_allsky_mj_m2_day", "mean"),
    ).reset_index()
    # A sum over missing months is not a zero: rain or evaporation with any missing month becomes NaN.
    for col, src in [("q_rain_mm", "rain_mm"), ("q_pet_mm", "pet_mm")]:
        full = m.groupby(["cell_id", "year", "quarter"])[src].count().to_numpy() == 3
        agg.loc[~full, col] = np.nan
    if not (agg["n_months"] == 3).all():
        raise ValueError("A quarter does not have its 3 months.")
    statics = monthly_panel.drop_duplicates("cell_id").set_index("cell_id")[["lat", "lon", *SOIL]]
    df = agg.merge(statics, left_on="cell_id", right_index=True, how="left")
    df = df.merge(veg, on=["cell_id", "year", "quarter"], how="left", validate="one_to_one")
    df = df.sort_values(["cell_id", "year", "quarter"]).reset_index(drop=True)
    df["quarter_id"] = df["year"] * 4 + df["quarter"] - 1
    g = df.groupby("cell_id", sort=False)
    df["q_rain_mm_lag1"] = g["q_rain_mm"].shift(1)
    df["ndvi_lag1"] = g["ndvi"].shift(1)
    df["ndvi_lag4"] = g["ndvi"].shift(4)
    return df
