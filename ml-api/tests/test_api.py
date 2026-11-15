"""Essential integration tests: real models, real data cube. Run from ml-api/: python -m pytest -q"""
import math

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
client.__enter__()   # runs the startup (model loading)


def sm_features(**over):
    f = {"rain_mm": 20.0, "rain_mm_lag1": 10.0, "rain_mm_lag2": 5.0, "rain_mm_sum6": 60.0, "t2m_c": 25.0, "pet_mm": 120.0,
         "pet_mm_lag1": 115.0, "sm_root_m3m3_lag1": 0.25, "sm_surface_m3m3_lag1": 0.22, "power_rh2m_pct": 75.0,
         "power_ws2m_ms": 3.0, "power_allsky_mj_m2_day": 20.0, "month_sin": math.sin(2 * math.pi * 2 / 12),
         "month_cos": math.cos(2 * math.pi * 2 / 12), "soil_nutrient_low_class": 2.0, "soil_oxygen_low_class": 3.0,
         "soil_lime_gypsum_class": 1.0, "soil_salinity_sodicity_class": 1.0, "soil_rooting_class": 2.0}
    return f | over


def test_health_and_info():
    h = client.get("/api/v1/health").json()
    assert h["model_loaded"] is True, h
    info = client.get("/api/v1/model/info").json()
    assert info["sm_root_monthly"]["algorithm"] == "XGBoost"
    assert info["sm_root_monthly"]["features_in_order"][0] == "rain_mm"
    assert info["sm_root_monthly"]["training_date"] is None   # not stored: reported, not invented


def test_prediction_matches_the_model_and_validates():
    r = client.post("/api/v1/predictions", json={"model": "sm_root_monthly", "features": sm_features()})
    assert r.status_code == 200, r.text
    body = r.json()
    assert 0 < body["prediction"] < 1 and body["interval_90"]["low"] < body["prediction"] < body["interval_90"]["high"]
    assert client.post("/api/v1/predictions", json={"model": "sm_root_monthly", "features": sm_features(rain_mm=-1)}).status_code == 422
    f = sm_features(); f.pop("t2m_c")
    assert client.post("/api/v1/predictions", json={"model": "sm_root_monthly", "features": f}).status_code == 422
    assert client.post("/api/v1/predictions", json={"model": "sm_root_monthly", "features": sm_features(extra=1)}).status_code == 422
    assert client.post("/api/v1/predictions", json={"model": "sm_root_monthly", "features": sm_features(t2m_c=None)}).status_code == 422


def test_simulation_drought_dries_and_baseline_matches_itself():
    loc = {"lat": -6.42, "lon": -79.73}
    same = client.post("/api/v1/simulations/climate", json={"location": loc, "horizon": 4}).json()
    assert all(c["absolute_difference"] == 0 for c in same["comparison"]), same["comparison"]
    r = client.post("/api/v1/simulations/climate", json={"location": loc, "horizon": 4, "scenario": {"dry_months": [2, 3]}})
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["periods"]) == 4 and body["baseline"]["members"] == 28
    assert body["comparison"][2]["absolute_difference"] < 0      # the drought case passed its check: it dries the soil
    assert body["modified_inputs"] and body["interpretation"]["summary"]


def test_simulation_errors():
    assert client.post("/api/v1/simulations/climate", json={"location": {"lat": 0, "lon": 0}}).status_code == 400
    assert client.post("/api/v1/simulations/climate", json={"location": {"lat": -6.42, "lon": -79.73}, "horizon": 20}).status_code == 422
    rain = client.post("/api/v1/simulations/climate", json={"location": {"lat": -6.42, "lon": -79.73}, "scenario": {"rain_factor": 2}}).json()
    assert rain["reliability"]["rain_only_change"] is True and "sanity checks" in rain["interpretation"]["limitations"][0]


def test_projections_match_the_validated_notebook():
    """The grid served to the web equals ml/notebooks/06_projections.ipynb (artifacts/projections), cell by cell."""
    from pathlib import Path
    import pandas as pd
    b = client.get("/api/v1/projections").json()
    assert set(b["soil_water"]) >= {"base", "el_nino", "drought_feb_mar", "usual"} and b["meta"]["start"] == "2025-12"
    art = pd.read_parquet(Path(__file__).resolve().parents[2] / "ml/artifacts/projections/projection_2026_cells.parquet")
    n = len(b["cells"]["x"])
    for i in (0, n // 3, n // 2, n - 1):                       # cells spread over the grid
        cid = f'{b["cells"]["x"][i]},{b["cells"]["y"][i]}'
        for scen in ("base", "el_nino", "drought_feb_mar"):
            ref = art[(art.cell_id == cid) & (art.variable == "soil_water_28_100cm") & (art.scenario == scen)].sort_values("lead")
            assert len(ref) == 12, cid
            got = b["soil_water"][scen]["median"][i * 12:(i + 1) * 12]
            assert [round(v * 1000) for v in ref["median"]] == got, (cid, scen)
    one = client.get("/api/v1/projections/cell", params={"lat": -6.42, "lon": -79.73}).json()
    assert len(one["median"]) == 12 and one["low_90"][0] <= one["median"][0] <= one["high_90"][0]


def test_ask_without_ai_says_so_and_enriches_context():
    from app import ask as sprout
    from app.config import settings
    object.__setattr__(settings, "llm_base_url", "http://127.0.0.1:9")   # nothing listens there
    r = client.post("/api/v1/ask", json={"question": "¿Cómo estará mi suelo?", "lang": "es", "context": {"lat": -6.42, "lon": -79.73}})
    assert r.status_code == 503 and r.json()["error"] == "ai_unavailable"
    ctx = sprout.enrich({"lat": -6.42, "lon": -79.73})
    assert len(ctx["model_projection_soil_water"]["el_nino"]["median"]) == 6
    assert "Sprout" in sprout.persona() and "---" not in sprout.persona()[:5]
    assert client.post("/api/v1/ask", json={"question": ""}).status_code == 422
