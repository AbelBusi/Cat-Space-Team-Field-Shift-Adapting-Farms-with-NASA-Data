"""Check T of docs/ML_TRENDS.md: does extending the 1998-2017 trend of each Lambayeque cell get closer to the yearly
values of 2018-2025 than "no change" (the 1998-2017 median)? Also the share of cells with a clear 1998-2025 trend and
its direction. Reads the API cube (the data the app shows). Writes ml/artifacts/trends/trend_check.json.

    ml/.venv/bin/python ml/scripts/trend_check.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ML = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML))
from fs_ml import evaluate as E, trends as T  # noqa: E402

z = np.load(ML.parent / "ml-api" / "data" / "cube.npz")
inside = z["province"] != "outside"
blocks = np.asarray(E.spatial_blocks(z["lat"], z["lon"]))[inside]
months = pd.DatetimeIndex(pd.to_datetime(z["dates"])).year.to_numpy()
quarters = np.array([int(q[:4]) for q in z["quarters"]])
out = {"rules": "docs/ML_TRENDS.md §2", "cells": int(inside.sum()), "variables": {}}
for name, (key, how, need) in T.VARIABLES.items():
    raw = z["ndvi"] if key == "ndvi" else z[f"v__{key}"]
    years, Y = T.yearly(raw[inside].astype(float), quarters if key == "ndvi" else months, how, need)
    fit, test = years <= 2017, (years >= 2018) & (years <= 2025)
    y_obs, p_trend, p_flat, blk = [], [], [], []
    clear_up = clear_down = fitted = 0
    for c in range(Y.shape[0]):
        t = T.theil_sen(years[fit], Y[c, fit])
        full = T.theil_sen(years[years <= 2025], Y[c, years <= 2025])
        if full:
            fitted += 1
            clear_up += full["clear"] and full["slope"] > 0
            clear_down += full["clear"] and full["slope"] < 0
        if not t:
            continue
        obs = Y[c, test]; ok = np.isfinite(obs)
        if not ok.any():
            continue
        y_obs += list(obs[ok]); p_trend += list((t["intercept"] + t["slope"] * years[test])[ok])
        p_flat += [float(np.nanmedian(Y[c, fit]))] * int(ok.sum()); blk += [blocks[c]] * int(ok.sum())
    ci = E.block_bootstrap(np.array(y_obs), {"trend": np.array(p_trend), "no_change": np.array(p_flat)}, np.array(blk), "trend", 1000, 42).set_index(["model", "metric"])
    sk = ci.loc[("trend", "skill vs no_change")]
    out["variables"][name] = {"rows_2018_2025": len(y_obs), "skill_trend_vs_no_change": float(sk.value), "ci": [float(sk.ci_low), float(sk.ci_high)],
                              "trend_helps": bool(sk.ci_low > 0), "cells_with_trend": fitted,
                              "share_clear_up_1998_2025": clear_up / max(1, fitted), "share_clear_down_1998_2025": clear_down / max(1, fitted)}
    print(name, json.dumps(out["variables"][name]))
art = ML / "artifacts" / "trends"; art.mkdir(parents=True, exist_ok=True)
(art / "trend_check.json").write_text(json.dumps(out, indent=1))
