"""Loaders for the team's raw files (Google Earth Engine exports, NASA POWER CSVs, FAO GAEZ JSONs).

Only unit conversions happen here, no new variables. Each loader takes `years=(first, last)` and keeps only the rows
inside that window, so a phase never holds rows from another phase in memory; it only reports how many it left out.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

# Side of one grid cell in degrees, read from the GEE polygons (about 2 km). Cell ids are "x,y" with
# x = floor(lon / GRID_STEP) and y = floor(lat / GRID_STEP), so the id alone gives the cell's position.
GRID_STEP = 0.017966305682390427

# Paths inside the team folder "Datos para proyecto Nasa" (set FIELDSHIFT_RAW_DIR to that folder).
RAW_FILES = {
    "gee_monthly": "Hídrico/GEE_2km_Clima_Humedad_Mensual_1998_01_a_2026_11.csv",
    "gee_quarterly": "Hídrico/GEE_2km_Veg_Salinidad_Trimestral_1998_Q1_a_2026_Q4.csv",
    "gee_s2_scenes": "Hídrico/Lambayeque_Grilla_2km.csv",
    "power_t2m": "Clima y metereología/Temperature at 2 Meters_Monthly_1998_2017.csv",
    "power_rh2m": "Clima y metereología/Relative Humidity at 2 Meters_Monthly_1998_2017.csv",
    "power_ws2m": "Clima y metereología/Wind Speed at 2 Meters_Monthly_1998_2017.csv",
    "power_allsky": "Clima y metereología/All Sky Surface Shortwave Downward Irradiance_Monthly_1998_2017.csv",
    # Validation years (2018-2022), same grid and parameters, delivered as separate files.
    "power_t2m_2018_2022": "Clima y metereología/Temperature at 2 Meters_Monthly_2018_2022.csv",
    "power_rh2m_2018_2022": "Clima y metereología/Relative Humidity at 2 Meters_Monthly_2018_2022.csv",
    "power_ws2m_2018_2022": "Clima y metereología/Wind Speed at 2 Meters_Monthly_2018_2022.csv",
    "power_allsky_2018_2022": "Clima y metereología/All Sky Surface Shortwave Downward Irradiance_Monthly_2018_2022.csv",
    # Testing years (2023-2025; 2026 has no complete data yet).
    "power_t2m_2023_2025": "Clima y metereología/Temperature at 2 Meters_Monthly_2023_2025.csv",
    "power_rh2m_2023_2025": "Clima y metereología/Relative Humidity at 2 Meters_Monthly_2023_2025.csv",
    "power_ws2m_2023_2025": "Clima y metereología/Wind Speed at 2 Meters_Monthly_2023_2025.csv",
    "power_allsky_2023_2025": "Clima y metereología/All Sky Surface Shortwave Downward Irradiance_Monthly_2023_2025.csv",
    "gaez_nutrient_low": "Suelos/Nutrient Availability low.json",
    "gaez_oxygen_high": "Suelos/Oxygen Availability High.json",
    "gaez_oxygen_low": "Suelos/Oxygen Availability Low.json",
    "gaez_lime_gypsum_high": "Suelos/Presence of lime and gypsum High.json",
    "gaez_lime_gypsum_low": "Suelos/Presence of lime and gypsum Low.json",
    "gaez_salinity_high": "Suelos/Presence of salinity and sodicity High.json",
    "gaez_salinity_low": "Suelos/Presence of salinity and sodicity Low.json",
    "gaez_rooting_high": "Suelos/Rooting Conditions High.json",
    "gaez_rooting_low": "Suelos/Rooting Conditions Low.json",
}

# NASA POWER parameter -> column name in our tables (unit in the name).
POWER_COLUMNS = {"T2M": "power_t2m_c", "RH2M": "power_rh2m_pct", "WS2M": "power_ws2m_ms",
                 "ALLSKY_SFC_SW_DWN": "power_allsky_mj_m2_day"}
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def raw_dir() -> Path:
    d = Path(os.environ.get("FIELDSHIFT_RAW_DIR", Path(__file__).resolve().parents[1] / "data" / "raw"))
    if not d.is_dir():
        raise FileNotFoundError(f"Raw data folder not found: {d}. Set FIELDSHIFT_RAW_DIR to 'Datos para proyecto Nasa'.")
    return d


def raw_path(key: str) -> Path:
    return raw_dir() / RAW_FILES[key]


def sha256(path: Path, chunk: int = 1 << 22) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while b := f.read(chunk):
            h.update(b)
    return h.hexdigest()


def _split_index(index: pd.Series) -> tuple[pd.Series, pd.Series]:
    """GEE 'system:index' is '<prefix>_<x>,<y>': the prefix is the image (date or quarter number), the rest the cell."""
    parts = index.str.split("_", n=1)
    return parts.str[0], parts.str[1]


def load_gee_monthly(years: tuple[int, int]) -> tuple[pd.DataFrame, dict]:
    """Monthly 2 km table (CHIRPS rain, ERA5-Land temperature, potential evaporation, soil water layers 1 and 3).

    Unit conversions only: K -> °C, potential evaporation (m, negative = upward flux in ECMWF's convention) -> mm,
    positive. The constant column `max` (always 1) and the polygon text `.geo` are not loaded.
    """
    cols = ["system:index", "fecha_mensual", "lluvia_chirps_mm", "potential_evaporation_sum", "temperature_2m",
            "volumetric_soil_water_layer_1", "volumetric_soil_water_layer_3"]
    df = pd.read_csv(raw_path("gee_monthly"), usecols=cols)
    year = df["fecha_mensual"].str[:4].astype(int)
    keep = year.between(*years)
    info = {"rows_total": int(len(df)), "rows_kept": int(keep.sum()), "rows_outside_window_not_used": int((~keep).sum())}
    df = df[keep].copy()
    prefix, df["cell_id"] = _split_index(df["system:index"])
    info["index_prefix_matches_month"] = bool((prefix.values == df["fecha_mensual"].str.replace("-", "").values).all())
    df["date"] = pd.to_datetime(df["fecha_mensual"] + "-01")
    out = pd.DataFrame({
        "cell_id": df["cell_id"].values,
        "date": df["date"].values,
        "rain_mm": df["lluvia_chirps_mm"].values,
        "t2m_c": df["temperature_2m"].values - 273.15,
        "pet_mm": -df["potential_evaporation_sum"].values * 1000.0,
        "sm_surface_m3m3": df["volumetric_soil_water_layer_1"].values,
        "sm_root_m3m3": df["volumetric_soil_water_layer_3"].values,
    })
    return out.sort_values(["cell_id", "date"]).reset_index(drop=True), info


def load_gee_quarterly(years: tuple[int, int]) -> tuple[pd.DataFrame, dict]:
    """Quarterly 2 km vegetation table. `fecha_trimestral` is the first month of the quarter (01, 04, 07, 10)."""
    cols = ["system:index", "fecha_trimestral", "NDVI", "NDSI_Salinidad"]
    df = pd.read_csv(raw_path("gee_quarterly"), usecols=cols)
    year = df["fecha_trimestral"].str[:4].astype(int)
    keep = year.between(*years)
    info = {"rows_total": int(len(df)), "rows_kept": int(keep.sum()), "rows_outside_window_not_used": int((~keep).sum())}
    df = df[keep].copy()
    _, df["cell_id"] = _split_index(df["system:index"])
    month = df["fecha_trimestral"].str[5:7].astype(int)
    out = pd.DataFrame({
        "cell_id": df["cell_id"].values,
        "year": year[keep].values,
        "quarter": ((month - 1) // 3 + 1).values,
        "ndvi": df["NDVI"].values,
        "ndsi_salinidad": df["NDSI_Salinidad"].values,
    })
    return out.sort_values(["cell_id", "year", "quarter"]).reset_index(drop=True), info


def load_power(key: str, years: tuple[int, int]) -> tuple[pd.DataFrame, dict]:
    """NASA POWER regional monthly CSV (wide: JAN..DEC, ANN) -> long table. ANN (the yearly mean) is dropped: it
    contains the months after each month, so it must never be a feature. -999 (POWER's missing value) -> NaN."""
    text = raw_path(key).read_text(encoding="utf-8")
    lines = text.splitlines()
    end = next(i for i, l in enumerate(lines) if l.strip() == "-END HEADER-")
    header = "\n".join(lines[:end + 1])
    wide = pd.read_csv(io.StringIO("\n".join(lines[end + 1:])))
    param = wide["PARAMETER"].unique()
    assert len(param) == 1, param
    info = {"parameter": str(param[0]), "header": header, "rows_wide": int(len(wide)),
            "duplicate_rows": int(wide.duplicated(["YEAR", "LAT", "LON"]).sum()),
            "missing_-999": int((wide[MONTHS] == -999).sum().sum())}
    wide = wide[wide["YEAR"].between(*years)]
    long = wide.melt(id_vars=["YEAR", "LAT", "LON"], value_vars=MONTHS, var_name="m", value_name="value")
    long["value"] = long["value"].replace(-999, np.nan)
    long["date"] = pd.to_datetime(dict(year=long["YEAR"], month=long["m"].map({m: i + 1 for i, m in enumerate(MONTHS)}), day=1))
    col = POWER_COLUMNS[info["parameter"]]
    out = long.rename(columns={"LAT": "power_lat", "LON": "power_lon", "value": col})[["power_lat", "power_lon", "date", col]]
    return out.sort_values(["power_lat", "power_lon", "date"]).reset_index(drop=True), info


def load_gaez(key: str) -> tuple[pd.DataFrame, dict]:
    """FAO GAEZ soil layer exported as JSON pixels (5 arc-minute grid, about 9 km). Values are class codes."""
    j = json.loads(raw_path(key).read_text(encoding="utf-8"))
    px = pd.DataFrame(j["pixels"])
    meta = j["dataset"]
    px = px[px["value"] != meta.get("nodata_value", 255.0)]
    return px[["row", "col", "latitude", "longitude", "value"]].reset_index(drop=True), meta


def cells_from_ids(ids: pd.Series) -> pd.DataFrame:
    """Cell centers from the 'x,y' ids."""
    u = pd.Series(sorted(ids.unique()))
    xy = u.str.split(",", expand=True).astype(int)
    return pd.DataFrame({"cell_id": u, "x": xy[0], "y": xy[1],
                         "lon": (xy[0] + 0.5) * GRID_STEP, "lat": (xy[1] + 0.5) * GRID_STEP})


def provinces_of(cells: pd.DataFrame) -> pd.Series:
    """Province of each cell center, from the OpenStreetMap boundaries the web app uses; 'outside' if none."""
    from matplotlib.path import Path as Poly
    admin = json.loads((Path(__file__).resolve().parents[2] / "web/src/data/lambayeque_admin.json").read_text(encoding="utf-8"))
    pts = cells[["lon", "lat"]].to_numpy()
    out = np.full(len(cells), "outside", dtype=object)
    for prov in admin["provinces"]:
        inside = np.zeros(len(cells), bool)
        for ring in prov["rings"]:
            inside ^= Poly(np.asarray(ring)).contains_points(pts)   # rings are [lon, lat]; holes cancel out
        out[inside & (out == "outside")] = prov["name"]
    return pd.Series(out, index=cells.index, name="province")


def check_cell_geometry(n: int = 200) -> float:
    """Largest distance (degrees) between the center computed from an id and the center of its GEE polygon."""
    df = pd.read_csv(raw_path("gee_monthly"), usecols=["system:index", ".geo"], nrows=n)
    _, ids = _split_index(df["system:index"])
    calc = cells_from_ids(ids).set_index("cell_id")
    worst = 0.0
    for cid, geo in zip(ids, df[".geo"]):
        ring = np.array(json.loads(geo)["coordinates"][0])
        lon, lat = ring[:-1, 0].mean(), ring[:-1, 1].mean()
        worst = max(worst, abs(lon - calc.at[cid, "lon"]), abs(lat - calc.at[cid, "lat"]))
    return worst
