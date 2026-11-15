"""ERA5-Land's own monthly rain (the rain that drives the soil water target), used only by the v3 model.

Source: GEE `ECMWF/ERA5_LAND/MONTHLY_AGGR`, exported per 2 km cell (`GEE_2km_ERA5L_lluvia_capa2_1998_2026.csv`).
`total_precipitation_sum` is metres per month → mm. It is 3-6 times wetter than CHIRPS on this coast (docs/ML_V3_ERA5_RAIN.md):
a model input, never "the rain" shown to users."""
from pathlib import Path

import pandas as pd

from . import data as D

ERA5_FILE = "Hídrico/GEE_2km_ERA5L_lluvia_capa2_1998_2026.csv"
FEATURES = ["era5_rain_mm", "era5_rain_mm_lag1", "era5_rain_mm_lag2", "era5_rain_mm_sum6"]


def load_era5_rain(cells=None, path: Path | None = None) -> pd.DataFrame:
    path = Path(path) if path else D.raw_dir() / ERA5_FILE
    d = pd.read_csv(path, usecols=["system:index", "fecha_mensual", "total_precipitation_sum"])
    d["cell_id"] = d["system:index"].str.split("_", n=1).str[1]
    if cells is not None:
        d = d[d.cell_id.isin(set(cells))]
    return pd.DataFrame({"cell_id": d.cell_id.to_numpy(), "date": pd.to_datetime(d.fecha_mensual + "-01").to_numpy(),
                         "era5_rain_mm": (d.total_precipitation_sum * 1000).to_numpy()})


def load_era5_layer2(cells, dates, path: Path | None = None):
    """Soil water of ERA5-Land layer 2 (7-28 cm), (cells, months) in the given order; NaN where missing. Shown in the
    app next to layers 1 and 3 (the field's timeline); not an input of any model."""
    import numpy as np
    path = Path(path) if path else D.raw_dir() / ERA5_FILE
    d = pd.read_csv(path, usecols=["system:index", "fecha_mensual", "volumetric_soil_water_layer_2"])
    d["cell_id"] = d["system:index"].str.split("_", n=1).str[1]
    d = d[d.cell_id.isin(set(cells))]
    wide = d.pivot_table(index="cell_id", columns="fecha_mensual", values="volumetric_soil_water_layer_2", aggfunc="first")
    cols = [f"{x:%Y-%m}" for x in pd.DatetimeIndex(dates)]
    return wide.reindex(index=list(cells), columns=cols).to_numpy(dtype=float)


def add_to_monthly(panel: pd.DataFrame, era5: pd.DataFrame) -> pd.DataFrame:
    """Same-month value, lags 1-2 and the 6-month sum, inside each cell (as fs_ml.features does for CHIRPS)."""
    out = panel.merge(era5, on=["cell_id", "date"], how="left", validate="one_to_one").sort_values(["cell_id", "date"])
    g = out.groupby("cell_id", sort=False)["era5_rain_mm"]
    out["era5_rain_mm_lag1"], out["era5_rain_mm_lag2"] = g.shift(1), g.shift(2)
    out["era5_rain_mm_sum6"] = g.transform(lambda s: s.rolling(6, min_periods=6).sum())
    return out.reset_index(drop=True)
