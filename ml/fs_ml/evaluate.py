"""Metrics, baselines, training-range checks and split-conformal intervals, shared by every phase."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def regression_metrics(y, p) -> dict:
    """MAE, RMSE, R², mean bias. MAPE is left out on purpose: NDVI crosses zero, so a percentage error is undefined."""
    y, p = np.asarray(y, float), np.asarray(p, float)
    ok = ~(np.isnan(y) | np.isnan(p))
    y, p = y[ok], p[ok]
    err = p - y
    ss_tot = ((y - y.mean()) ** 2).sum()
    return {"n": int(len(y)), "MAE": float(np.abs(err).mean()), "RMSE": float(np.sqrt((err ** 2).mean())),
            "R2": float(1 - (err ** 2).sum() / ss_tot) if ss_tot > 0 else float("nan"), "bias": float(err.mean())}


def skill(rmse_model: float, rmse_baseline: float) -> float:
    """RMSE skill score: 1 = perfect, 0 = no better than the baseline, < 0 = worse than the baseline."""
    return float(1 - rmse_model / rmse_baseline)


def climatology(df: pd.DataFrame, target: str, keys: list[str], season: str) -> dict:
    """Mean of the target per cell and season (month or quarter), with the season mean as fallback for a cell that
    has no value for that season. Fitted on training rows only."""
    return {"by_cell": df.groupby(keys)[target].mean(), "by_season": df.groupby(season)[target].mean(),
            "keys": keys, "season": season}


def predict_climatology(clim: dict, df: pd.DataFrame) -> np.ndarray:
    idx = pd.MultiIndex.from_frame(df[clim["keys"]])
    p = clim["by_cell"].reindex(idx).to_numpy()
    fallback = clim["by_season"].reindex(df[clim["season"]]).to_numpy()
    return np.where(np.isnan(p), fallback, p)


def feature_bounds(X: pd.DataFrame) -> dict:
    """Training range of every feature, for the out-of-range warnings of later phases and of the simulator."""
    out = {}
    for c in X.columns:
        s = X[c].dropna()
        out[c] = {"min": float(s.min()), "p01": float(s.quantile(0.01)), "p50": float(s.median()),
                  "p99": float(s.quantile(0.99)), "max": float(s.max()), "missing_share": float(X[c].isna().mean())}
    return out


def out_of_range(X: pd.DataFrame, bounds: dict, strict: bool = False) -> pd.Series:
    """True where any feature is outside the training [p01, p99] (or [min, max] when strict)."""
    lo, hi = ("min", "max") if strict else ("p01", "p99")
    flags = pd.Series(False, index=X.index)
    for c, b in bounds.items():
        v = X[c]
        flags |= (v < b[lo]) | (v > b[hi])
    return flags


def spatial_blocks(lat, lon, size_deg: float = 0.2) -> np.ndarray:
    """Block id of size_deg x size_deg squares (0.2° ≈ 22 km, larger than one ERA5-Land pixel)."""
    return (np.floor(np.asarray(lat) / size_deg).astype(int) * 10000 + np.floor(np.asarray(lon) / size_deg).astype(int))


def block_bootstrap(y, preds: dict, blocks, reference: str, n_boot: int = 1000, seed: int = 42,
                    level: float = 0.95) -> pd.DataFrame:
    """Confidence intervals of MAE, RMSE, R², bias and RMSE skill (vs every other entry of `preds`), resampling whole
    spatial blocks with replacement (all years of a block move together, so neighbour cells that repeat the same
    ERA5-Land pixel are not counted as independent evidence). `reference` is the model whose skill is reported."""
    y = np.asarray(y, float)
    code, _ = pd.factorize(pd.Series(blocks))
    nb = code.max() + 1
    rng = np.random.default_rng(seed)
    W = rng.multinomial(nb, np.full(nb, 1 / nb), size=n_boot).astype(float)       # (n_boot, blocks)
    sums = lambda v: np.bincount(code, weights=v, minlength=nb)
    n = W @ sums(np.ones_like(y)); sy = W @ sums(y); syy = W @ sums(y * y)
    ss_tot = syy - sy ** 2 / n
    reps, point = {}, {}
    for name, p in preds.items():
        e = np.asarray(p, float) - y
        se, sae, sbias = W @ sums(e * e), W @ sums(np.abs(e)), W @ sums(e)
        reps[name] = {"MAE": sae / n, "RMSE": np.sqrt(se / n), "R2": 1 - se / ss_tot, "bias": sbias / n}
        point[name] = regression_metrics(y, p)
    for name in preds:
        if name != reference:
            reps[reference][f"skill vs {name}"] = 1 - reps[reference]["RMSE"] / reps[name]["RMSE"]
            point[reference][f"skill vs {name}"] = skill(point[reference]["RMSE"], point[name]["RMSE"])
    a = (1 - level) / 2
    rows = []
    for name, metrics in reps.items():
        for m, v in metrics.items():
            rows.append({"model": name, "metric": m, "value": point[name][m],
                         "ci_low": float(np.quantile(v, a)), "ci_high": float(np.quantile(v, 1 - a))})
    return pd.DataFrame(rows)


def coverage_ci(inside, blocks, n_boot: int = 1000, seed: int = 42, level: float = 0.95) -> tuple[float, float, float]:
    """Share of observations inside their interval, with a block-bootstrap confidence interval."""
    inside = np.asarray(inside, float)
    code, _ = pd.factorize(pd.Series(blocks))
    nb = code.max() + 1
    W = np.random.default_rng(seed).multinomial(nb, np.full(nb, 1 / nb), size=n_boot)
    k = W @ np.bincount(code, weights=inside, minlength=nb)
    n = W @ np.bincount(code, minlength=nb)
    a = (1 - level) / 2
    return float(inside.mean()), float(np.quantile(k / n, a)), float(np.quantile(k / n, 1 - a))


def conformal_halfwidth(residuals, coverage: float) -> float:
    """Split-conformal half-width: the ceil((n + 1) * coverage)-th smallest absolute residual of a calibration set
    the model never trained on. Valid only if calibration and future errors are exchangeable."""
    r = np.sort(np.abs(np.asarray(residuals, float)))
    k = min(len(r), math.ceil((len(r) + 1) * coverage))
    return float(r[k - 1])
