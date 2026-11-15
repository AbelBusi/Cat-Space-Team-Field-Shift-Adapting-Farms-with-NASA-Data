"""What the API loads once at startup: the tested models, the data cube, the result cards and the precomputed layers.
The loading error (if any) is kept, never hidden: /health reports it and inference answers 503."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..config import settings
from .common import ModelUnavailable, log


@dataclass
class State:
    models: dict
    cube: object
    proj_card: dict
    sha: dict
    skill: pd.DataFrame
    checks: dict = field(default_factory=dict)          # Phase 2 results (ml/artifacts/api_validation/checks.json)
    bundle: dict | None = None                          # projections of the whole grid
    risk: np.ndarray | None = None                      # share of analog members below the cell's 20th percentile
    sm_cols: dict | None = None                         # model inputs of every cell and month (observed)
    nd_cols: dict | None = None
    sm_pred: np.ndarray | None = None                   # one-step predictions of every cell and month
    nd_pred: np.ndarray | None = None
    cache: dict = field(default_factory=dict)


STATE: State | None = None
LOAD_ERROR: str | None = None


def _sha(p) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load() -> None:
    """Called once at startup. Checks every file, the feature order and the model hashes."""
    global STATE, LOAD_ERROR
    t0 = time.time()
    try:
        for p in (settings.model_dir, settings.ml_package_dir / "fs_ml", settings.cube_path, settings.projection_card):
            if not p.exists():
                raise FileNotFoundError(f"missing: {p.name} (see README: paths and FS_* variables)")
        if str(settings.ml_package_dir) not in sys.path:
            sys.path.insert(0, str(settings.ml_package_dir))
        from fs_ml.predict import load as load_model
        from fs_ml import project as P
        from . import features, projections

        models, sha = {}, {}
        for name in ("sm_root_monthly", "ndvi_quarterly"):
            m = load_model(name, settings.model_dir)       # asserts the booster's feature names = preprocessing order
            sha[name] = _sha(settings.model_dir / name / "model.ubj")
            if sha[name] != m["card"]["sha256"]:
                raise RuntimeError(f"{name}: model file does not match its model card (sha256)")
            models[name] = m
        z = np.load(settings.cube_path, allow_pickle=False)
        cells = pd.DataFrame({"cell_id": z["cell_id"], "lat": z["lat"], "lon": z["lon"], "province": z["province"],
                              "district": z["district"], **{k.split("__")[1]: z[k] for k in z.files if k.startswith("soil__")}})
        cube = P.Cube(cells=cells, dates=pd.DatetimeIndex(pd.to_datetime(z["dates"])),
                      v={k.split("__")[1]: z[k].astype(float) for k in z.files if k.startswith("v__")},
                      quarters=pd.PeriodIndex(z["quarters"], freq="Q"), ndvi=z["ndvi"].astype(float))
        checks = json.loads(settings.api_checks.read_text())["checks"] if settings.api_checks.exists() else {}
        s = State(models=models, cube=cube, proj_card=json.loads(settings.projection_card.read_text()), sha=sha,
                  skill=pd.read_csv(settings.projection_card.with_name("hindcast_skill_by_lead.csv")), checks=checks)
        s.sm_cols, s.nd_cols = features.sm_matrix(cube), features.nd_matrix(cube)
        s.sm_pred = features.predict_matrix(models["sm_root_monthly"], s.sm_cols)
        s.nd_pred = features.predict_matrix(models["ndvi_quarterly"], s.nd_cols)
        s.bundle, s.risk = projections.build_bundle(s)
        STATE, LOAD_ERROR = s, None
        log.info("loaded in %.1f s: models %s | cube %d cells %s..%s | phase 2 checks: %s", time.time() - t0,
                 {k: v[:12] for k, v in sha.items()}, len(cells), cube.dates[0].date(), cube.dates[-1].date(),
                 {k: v.get("pass") for k, v in sorted(checks.items())} or "not found")
    except Exception as e:      # reported by /health and as 503, never hidden
        STATE, LOAD_ERROR = None, f"{type(e).__name__}: {e}"
        log.exception("model loading failed")


def get() -> State:
    if STATE is None:
        raise ModelUnavailable(LOAD_ERROR or "models not loaded")
    return STATE


def check(code: str) -> dict:
    """A Phase 2 check: {'pass': bool, ...}; missing = not run (treated as failed)."""
    return (STATE.checks if STATE else {}).get(code, {"pass": False, "status": "not run"})
