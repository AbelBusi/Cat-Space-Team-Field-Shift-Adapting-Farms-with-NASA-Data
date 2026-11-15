"""Use the final (tested) models: prediction, prediction interval and out-of-range warning for each row.

    from fs_ml.predict import load, predict
    m = load("sm_root_monthly")
    out = predict(m, table)   # table built with fs_ml.features (same columns as Training)

The interval is split conformal, calibrated on 2018-2022, one width per season; its real coverage on 2023-2025 is in
`intervals.json` ("tested_coverage"). It is not a probability and not a guarantee.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

FINAL = Path(__file__).resolve().parents[1] / "artifacts" / "final_model"


def season_of(name: str, df: pd.DataFrame) -> pd.Series:
    """Season used for the interval width: rainy Jan-Apr / dry May-Dec (soil water), quarter (NDVI)."""
    if name.startswith("sm"):
        return pd.Series(np.where(df["month"] <= 4, "wet Jan-Apr", "dry May-Dec"), index=df.index)
    return "Q" + df["quarter"].astype(int).astype(str)


def load(name: str, root: Path = FINAL) -> dict:
    d = root / name
    model = xgb.XGBRegressor()
    model.load_model(d / "model.ubj")
    prep = json.loads((d / "preprocessing.json").read_text())
    intervals = json.loads((d / "intervals.json").read_text())
    card = json.loads((d / "model_card.json").read_text())
    assert model.get_booster().feature_names == prep["feature_names_in_order"]
    return {"name": name, "model": model, "features": prep["feature_names_in_order"],
            "bounds": prep["training_feature_bounds"], "intervals": intervals, "card": card}


def predict(m: dict, df: pd.DataFrame) -> pd.DataFrame:
    """Columns: prediction, low, high (90 % interval by season), out_of_range (outside training p01-p99),
    far_out_of_range (outside training min-max), unit."""
    X = df[m["features"]]
    pred = m["model"].predict(X)
    width = season_of(m["name"], df).map(m["intervals"]["half_width_90_by_season"]).to_numpy(float)
    soft = np.zeros(len(df), bool)
    hard = np.zeros(len(df), bool)
    for c, b in m["bounds"].items():
        v = X[c].to_numpy(float)
        soft |= (v < b["p01"]) | (v > b["p99"])
        hard |= (v < b["min"]) | (v > b["max"])
    return pd.DataFrame({"prediction": pred, "low": pred - width, "high": pred + width,
                         "out_of_range": soft, "far_out_of_range": hard,
                         "unit": m["card"]["target"]["unit"]}, index=df.index)
