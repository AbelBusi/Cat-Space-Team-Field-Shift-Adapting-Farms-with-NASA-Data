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
    sim: dict | None = None                             # the soil water model that runs simulations (v3 if accepted, else v1)
    primary: dict = field(default_factory=lambda: {"soil_water": "sm_root_monthly", "ndvi": "ndvi_quarterly"})
    proj: dict | None = None                            # corrections, useful lead, skill and coverage of the projections in use
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
        s.sim = _simulation_model(s, models["sm_root_monthly"])
        if s.sim["version"] == "v3":            # v3 becomes the soil water model of the whole app; v1 stays as reference
            models["sm_root_monthly_v3"] = s.sim; sha["sm_root_monthly_v3"] = s.sim["sha256"]
            s.primary["soil_water"] = "sm_root_monthly_v3"
        s.proj = _projection_config(s)
        s.sm_cols, s.nd_cols = features.sm_matrix(cube), features.nd_matrix(cube)
        s.sm_pred = features.predict_matrix(models[s.primary["soil_water"]], s.sm_cols)
        s.nd_pred = features.predict_matrix(models["ndvi_quarterly"], s.nd_cols)
        s.bundle, s.risk = projections.build_bundle(s)
        STATE, LOAD_ERROR = s, None
        log.info("loaded in %.1f s: models %s | cube %d cells %s..%s | phase 2 checks: %s", time.time() - t0,
                 {k: v[:12] for k, v in sha.items()}, len(cells), cube.dates[0].date(), cube.dates[-1].date(),
                 {k: v.get("pass") for k, v in sorted(checks.items())} or "not found")
    except Exception as e:      # reported by /health and as 503, never hidden
        STATE, LOAD_ERROR = None, f"{type(e).__name__}: {e}"
        log.exception("model loading failed")


def _simulation_model(s: State, v1: dict) -> dict:
    """v3 runs the simulations when its rules passed (R1 and R2) and the cube has ERA5-Land rain; otherwise v1.
    Each carries its own range corrections, useful lead, error and scenario checks."""
    import xgboost as xgb
    rmse_v1 = v1["card"]["metrics"]["validation_2018_2022"]["RMSE"]["value"]
    fallback = {"name": "sm_root_monthly", "version": "v1", "model": v1["model"], "features": v1["features"], "bounds": v1["bounds"],
                "card": v1["card"], "sha256": s.sha["sm_root_monthly"], "rmse": rmse_v1,
                "corr": {int(k): v for k, v in s.proj_card["correction_by_lead"]["sm"].items()},
                "useful": s.proj_card["useful_lead"]["soil_water_months"], "coverage": s.proj_card["coverage_2023_2025"]["sm"]["coverage_90"],
                "checks": {k: s.checks.get(k, {"pass": False}) for k in ("S1", "S2", "S3", "S4")}}
    d = settings.v3_dir
    try:
        summ = json.loads((d / "summary.json").read_text())
        if summ.get("status") != "candidate" or not summ["decision"]["usable_for_simulations"] or "era5_rain_mm" not in s.cube.v:
            log.info("simulations use v1 (v3 not accepted or no ERA5-Land rain in the cube)"); return fallback
        if _sha(d / "sm_root_monthly" / "model.ubj") != summ["sha256"]:
            raise RuntimeError("v3 model file does not match its summary (sha256)")
        prep = json.loads((d / "sm_root_monthly" / "preprocessing.json").read_text())
        m = xgb.XGBRegressor(); m.load_model(d / "sm_root_monthly" / "model.ubj")
        assert m.get_booster().feature_names == prep["feature_names_in_order"]
        met = {r["metric"]: r for r in json.loads((d / "validation_metrics_ci.json").read_text())["validation_2018_2022"] if r["model"] == "v3"}
        intervals = json.loads((d / "sm_root_monthly" / "intervals.json").read_text())
        log.info("soil water model: v3 (ERA5-Land rain, monotone constraints): %s", summ["sha256"][:12])
        return {"name": "sm_root_monthly_v3", "version": "v3", "model": m, "features": prep["feature_names_in_order"],
                "bounds": prep["training_feature_bounds"], "card": _v3_card(v1["card"], summ, met, prep), "intervals": intervals,
                "sha256": summ["sha256"], "rmse": met["RMSE"]["value"],
                "corr": {int(k): v for k, v in summ["projections"]["correction_by_lead"].items()},
                "useful": summ["projections"]["useful_lead_months"], "coverage": summ["projections"]["coverage_90_2023_2025"],
                "checks": summ["scenario_checks"], "metrics_validation": met, "second_look": summ["second_look_2023_2025"],
                "rmse_v1": rmse_v1}
    except FileNotFoundError:
        log.info("simulations use v1 (no v3 artifacts)"); return fallback


def _v3_card(v1: dict, summ: dict, met: dict, prep: dict) -> dict:
    """v3's model card: v1's target, data and limits, with v3's own numbers (notebook 08)."""
    m = lambda k: {"value": met[k]["value"], "ci95": [met[k]["ci_low"], met[k]["ci_high"]]}
    sl = summ["second_look_2023_2025"]
    return v1 | {"name": "sm_root_monthly_v3", "version": "3.0 (validated, ERA5-Land rain)", "sha256": summ["sha256"], "trees": summ["trees"],
                 "features_in_order": prep["feature_names_in_order"], "hyperparameters": summ["hyperparameters"] | {"monotone_constraints": prep["monotone_constraints"]},
                 "metrics": {"validation_2018_2022": {k: m(k) for k in ("MAE", "RMSE", "R2", "bias", "skill vs persistence", "skill vs climatology", "skill vs v1")},
                             "testing_2023_2025_second_look": {"RMSE": sl["rmse_v3"], "skill vs v1": {"value": sl["skill_vs_v1"][0], "ci95": sl["skill_vs_v1"][1:]},
                                                               "march_2023_RMSE": sl["march_2023_rmse"]["v3"]}},
                 "test_verdict": "VALIDATED: rules R1 and R2 of docs/ML_V3_ERA5_RAIN.md pass; 2023-2025 is a second look, not a blind test",
                 "data": v1["data"] | {"sources": v1["data"]["sources"] + ["ERA5-Land total precipitation (model input only, 3-6x wetter than CHIRPS on this coast)"]},
                 "not_for": v1["not_for"] + ["Showing ERA5-Land rain as the real rain (it is a model input only)"],
                 "library_versions": summ["versions"]}


def _projection_config(s: State) -> dict:
    """Range corrections, useful lead, skill by lead and coverage of the projections: v3's (soil water from notebook 08,
    NDVI chained on v3 from ml/scripts/v3_ndvi_chain.py) when v3 is the soil water model, else the projection card's."""
    pc, sk = s.proj_card, s.skill[s.skill.period == "validation"]
    rows = lambda df: [{"lead": int(r.lead), "skill": round(r.skill, 3), "low": round(r.skill_ci_low, 3), "high": round(r.skill_ci_high, 3)} for r in df.itertuples()]
    v1 = {"soil_water_model": "v1", "corr_sm": {int(k): v for k, v in pc["correction_by_lead"]["sm"].items()},
          "corr_nd": {int(k): v for k, v in pc["correction_by_lead"]["ndvi"].items()}, "useful_lead": pc["useful_lead"],
          "skill_by_lead": {"soil_water": rows(sk[sk.variable == "sm"]), "ndvi": rows(sk[sk.variable == "ndvi"])},
          "coverage_2023_2025": {k: round(v["coverage_90"], 3) for k, v in pc["coverage_2023_2025"].items()}}
    chain = settings.v3_dir / "ndvi_chain.json"
    if s.sim["version"] != "v3" or not chain.exists():
        return v1
    nd = json.loads(chain.read_text()); smk = pd.read_csv(settings.v3_dir / "hindcast_skill_validation.csv")
    return {"soil_water_model": "v3", "corr_sm": s.sim["corr"], "corr_nd": {int(k): v for k, v in nd["correction_by_lead"].items()},
            "useful_lead": pc["useful_lead"] | {"soil_water_months": s.sim["useful"], "ndvi_quarters": nd["useful_lead_quarters"]},
            "skill_by_lead": {"soil_water": rows(smk), "ndvi": [{"lead": r["lead"], "skill": round(r["skill"], 3), "low": round(r["skill_ci_low"], 3),
                                                                  "high": round(r["skill_ci_high"], 3)} for r in nd["skill_by_lead_validation"]]},
            "coverage_2023_2025": {"sm": round(s.sim["coverage"], 3), "ndvi": round(nd["coverage_90_2023_2025"], 3)}}


def get() -> State:
    if STATE is None:
        raise ModelUnavailable(LOAD_ERROR or "models not loaded")
    return STATE


def check(code: str) -> dict:
    """A Phase 2 check: {'pass': bool, ...}; missing = not run (treated as failed)."""
    return (STATE.checks if STATE else {}).get(code, {"pass": False, "status": "not run"})
