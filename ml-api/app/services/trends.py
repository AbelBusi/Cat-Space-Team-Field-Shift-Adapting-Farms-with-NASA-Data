"""Trends 1998-2025 of every cell and their extension to 2030 (docs/ML_TRENDS.md). Computed once at startup from the
cube; check T's result is read from ml/artifacts/trends/trend_check.json and decides how the extension is labelled."""
from __future__ import annotations

import json

import numpy as np

from ..config import settings

UNITS = {"soil_water": "m3/m3", "temperature": "°C", "rain": "mm/year", "ndvi": "NDVI"}
LAST, UNTIL = 2025, 2030


def build(cube) -> dict:
    from fs_ml import trends as T
    months = cube.dates.year.to_numpy(); quarters = np.array([q.year for q in cube.quarters])
    out = {}
    for name, (key, how, need) in T.VARIABLES.items():
        raw = cube.ndvi if key == "ndvi" else cube.v[key]
        years, Y = T.yearly(np.asarray(raw, float), quarters if key == "ndvi" else months, how, need)
        keep = years <= LAST
        years, Y = years[keep], Y[:, keep]
        fits = [T.theil_sen(years, Y[c]) for c in range(Y.shape[0])]
        out[name] = {"years": years, "Y": Y, "fits": fits}
    path = settings.v3_dir.parent / "trends" / "trend_check.json"
    out["_check"] = json.loads(path.read_text())["variables"] if path.exists() else {}
    return out


def for_cell(tr: dict, i: int) -> dict:
    from fs_ml import trends as T
    res = {}
    for name in ("soil_water", "temperature", "rain", "ndvi"):
        d, f = tr[name], tr[name]["fits"][i]
        chk = tr["_check"].get(name, {})
        item = {"unit": UNITS[name], "years": d["years"].astype(int).tolist(),
                "yearly": [None if not np.isfinite(v) else round(float(v), 4) for v in d["Y"][i]],
                "check": {"trend_helps": chk.get("trend_helps"), "skill": chk.get("skill_trend_vs_no_change"), "ci": chk.get("ci")}}
        if f:
            ext = T.extend(f, range(LAST + 1, UNTIL + 1))
            item |= {"per_decade": round(f["slope"] * 10, 4), "per_decade_low": round(f["slope_low"] * 10, 4), "per_decade_high": round(f["slope_high"] * 10, 4),
                     "clear": f["clear"], "direction": "up" if f["clear"] and f["slope"] > 0 else "down" if f["clear"] else "none",
                     "line": {"from": [int(d["years"][0]), round(f["intercept"] + f["slope"] * d["years"][0], 4)], "to": [LAST, round(f["intercept"] + f["slope"] * LAST, 4)]},
                     "extension": {k: [round(v, 4) for v in vals] if k != "years" else vals for k, vals in ext.items()}}
        res[name] = item
    return res


def for_bundle(tr: dict, cells_idx: np.ndarray, K: int) -> dict:
    """Per-decade slope (× K) and clear flag of the web's cells, for the trend map."""
    out = {}
    for name in ("soil_water", "temperature", "rain", "ndvi"):
        fits = [tr[name]["fits"][i] for i in cells_idx]
        scale = K if name in ("soil_water", "ndvi") else 100        # °C and mm need fewer digits
        out[name] = {"scale": scale, "per_decade": [None if f is None else int(round(f["slope"] * 10 * scale)) for f in fits],
                     "clear": [None if f is None else int(f["clear"]) for f in fits], "unit": UNITS[name]}
    return out
