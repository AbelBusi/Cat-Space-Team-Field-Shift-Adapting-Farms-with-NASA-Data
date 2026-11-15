"""Model status, metrics and validation results. All metrics are historical, per period: never the precision of one
prediction."""
from __future__ import annotations

import pandas as pd

from ..config import settings
from . import state
from .common import TARGET_MEANING


def info() -> dict:
    s = state.get(); out = {}
    for name, m in s.models.items():
        c = m["card"]
        out[name] = {
            "name": name, "algorithm": "XGBoost", "estimator": c.get("estimator"), "version": c.get("version"),
            "sha256": s.sha[name], "target": c["target"] | {"meaning": TARGET_MEANING[name]},
            "features_in_order": m["features"], "hyperparameters": c.get("hyperparameters"), "trees": c.get("trees"),
            "training_date": None,
            "training_date_note": "Not stored in the model files. Trained on 1998-2017 data; artifacts committed on 2026-11-15 (git history).",
            "data": c.get("data"), "metrics": c.get("metrics"), "baseline_to_beat": c.get("baseline_to_beat"),
            "test_verdict": c.get("test_verdict"), "interval": {k: m["intervals"].get(k) for k in ("method", "nominal", "half_width_90_by_season", "tested_coverage")},
            "intended_use": c.get("intended_use"), "known_limitations": c.get("not_for"), "library_versions": c.get("library_versions"),
        }
    pc = s.proj_card
    out["projections"] = {"method": pc["method"], "soil_water_model": s.proj["soil_water_model"], "useful_lead": s.proj["useful_lead"],
                          "coverage_2023_2025": s.proj["coverage_2023_2025"], "skill_by_lead_validation": s.proj["skill_by_lead"],
                          "scenario_checks_v1": pc["scenario_checks"], "not_for": pc["not_for"]}
    out["app_models"] = s.primary | {"alerts": "sm_root_monthly (v1: check S6 was validated with it)"}
    return out


def metrics() -> dict:
    s = state.get()
    return {name: {"metrics_by_period": m["card"].get("metrics"), "baseline_to_beat": m["card"].get("baseline_to_beat"),
                   "interval_tested_coverage": m["intervals"].get("tested_coverage")} for name, m in s.models.items()} | {
        "note": "Historical metrics of each period (with 95 % block-bootstrap CI where available). They are not the precision of a single prediction."}


def health() -> dict:
    ok = state.STATE is not None
    return {"status": "ok" if ok else "degraded", "model_loaded": ok, "model_available": ok, "error": None if ok else state.LOAD_ERROR,
            "models": {k: v[:16] for k, v in state.STATE.sha.items()} if ok else None,
            "phase2_checks_loaded": bool(state.STATE and state.STATE.checks)}


def _records(df: pd.DataFrame) -> list:
    return df.astype(object).where(df.notna(), None).to_dict("records")      # NaN is not valid JSON


def _csv(path) -> list | str:
    return _records(pd.read_csv(path)) if path.exists() else "not available in this deployment"


def validation() -> dict:
    s = state.get(); art = settings.model_dir.parent
    out = {}
    for name in ("sm_root_monthly", "ndvi_quarterly"):
        out[name] = {"validation_2018_2022_criteria": _csv(art / "phase2_validation" / name / "criteria.csv"),
                     "testing_2023_2025_criteria": _csv(art / "phase3_testing" / name / "criteria.csv")}
    if s.sim["version"] == "v3":
        out["sm_root_monthly_v3"] = {"decision": s.sim["card"]["test_verdict"], "metrics": s.sim["card"]["metrics"],
                                     "scenario_checks": s.sim["checks"], "rules": "docs/ML_V3_ERA5_RAIN.md"}
    out["projections"] = {"soil_water_model": s.proj["soil_water_model"], "useful_lead": s.proj["useful_lead"],
                          "coverage_2023_2025": s.proj["coverage_2023_2025"], "skill_by_lead_validation": s.proj["skill_by_lead"],
                          "scenario_checks_v1": s.proj_card["scenario_checks"]}
    out["api_phase2_checks"] = {k: {kk: vv for kk, vv in v.items() if kk not in ("table", "calibration")} for k, v in s.checks.items()} or "not run"
    out["rules"] = ["docs/ML_PHASE1_TRAINING.md §10", "docs/ML_PROJECTIONS.md §3", "docs/ML_API_VALIDATION.md"]
    return out
