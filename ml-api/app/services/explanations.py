"""Why the model gave a number: exact TreeSHAP contributions from XGBoost (`pred_contribs=True`).
base value + sum of contributions = the prediction. They describe the model, not causes in the field."""
from __future__ import annotations

import numpy as np
import pandas as pd
import xgboost as xgb

from . import state
from .prediction import EXPLAIN_CACHE
from .common import NotFound


def explain(name: str, feats: dict, prediction_id: str | None = None) -> dict:
    m = state.get().models[name]
    X = pd.DataFrame([{f: (np.nan if feats[f] is None else feats[f]) for f in m["features"]}])[m["features"]]
    contrib = m["model"].get_booster().predict(xgb.DMatrix(X), pred_contribs=True)[0]
    base, parts = float(contrib[-1]), contrib[:-1]
    order = np.argsort(-np.abs(parts))
    return {"prediction_id": prediction_id, "model": name, "unit": m["card"]["target"]["unit"],
            "base_value": base, "prediction": float(base + parts.sum()),
            "contributions": [{"feature": m["features"][k], "value": feats[m["features"][k]], "contribution": float(parts[k])} for k in order],
            "method": "TreeSHAP (XGBoost pred_contribs): base value + contributions = prediction",
            "note": "Contributions describe how the model reached its number, not causes in the field."}


def by_id(prediction_id: str) -> dict:
    hit = EXPLAIN_CACHE.get(prediction_id)
    if not hit:
        raise NotFound("unknown or expired prediction_id: run the prediction again (ids are kept in memory only)")
    return explain(hit[0], hit[1], prediction_id)
