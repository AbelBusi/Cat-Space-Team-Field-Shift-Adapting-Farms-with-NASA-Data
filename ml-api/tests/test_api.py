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
    assert body["comparison"][2]["absolute_difference"] < 0      # the drought case dries this cell (its global check failed: see docs)
    assert body["modified_inputs"] and body["interpretation"]["summary"]


def test_simulation_errors():
    assert client.post("/api/v1/simulations/climate", json={"location": {"lat": 0, "lon": 0}}).status_code == 400
    assert client.post("/api/v1/simulations/climate", json={"location": {"lat": -6.42, "lon": -79.73}, "horizon": 20}).status_code == 422
    rain = client.post("/api/v1/simulations/climate", json={"location": {"lat": -6.42, "lon": -79.73}, "scenario": {"rain_factor": 2}}).json()
    assert rain["reliability"]["rain_only_change"] is True
    # simulations run with the v3 model (ERA5-Land rain, monotone): its rain check S3 passed, so rain is not experimental,
    # double rain never lowers the soil, and the ERA5 rain warning is always there
    assert rain["model"]["version"] == "v3" and rain["reliability_level"] != "experimental"
    assert all(c["absolute_difference"] >= -1e-9 for c in rain["comparison"])
    assert any(w["code"] == "era5_rain" for w in rain["warnings"])
    rec = client.post("/api/v1/simulations/recovery", json={"location": {"lat": -6.42, "lon": -79.73}, "drought_months": 3}).json()
    assert rec["reliability_level"] == "experimental"             # S4 failed with v3 too


def test_projections_match_the_engine_with_the_app_model():
    """The grid served to the web equals fs_ml.project run with the app's soil water model (v3), cell by cell, and the
    range corrections are v3's (notebook 08) and the NDVI chain's (ml/scripts/v3_ndvi_chain.py)."""
    import json
    import numpy as np
    from fs_ml import project as P
    from app.config import settings
    from app.services import state
    s = state.get()
    b = client.get("/api/v1/projections").json()
    assert b["meta"]["soil_water_model"] == "v3" and b["meta"]["start"] == "2025-12"
    assert set(b["soil_water"]) >= {"base", "el_nino", "drought_feb_mar", "rain_half", "rain_double", "usual"}
    assert b["meta"]["useful_lead"] == {"soil_water_months": 6, "ndvi_quarters": 4}
    chain = json.loads((settings.v3_dir / "ndvi_chain.json").read_text())
    assert s.proj["corr_nd"][1] == chain["correction_by_lead"]["1"]
    cid_all = s.cube.cells.cell_id.to_numpy(); start = s.cube.dates[-1]; n = len(b["cells"]["x"])
    for i in (0, n // 3, n - 1):
        cid = f'{b["cells"]["x"][i]},{b["cells"]["y"][i]}'; k = int((cid_all == cid).nonzero()[0][0])
        one = P.Cube(cells=s.cube.cells.iloc[[k]].reset_index(drop=True), dates=s.cube.dates, v={a: v[[k]] for a, v in s.cube.v.items()},
                     quarters=s.cube.quarters, ndvi=s.cube.ndvi[[k]])
        w = P.analog_weather(one, start, 12, range(1998, start.year + 1))
        med = np.quantile(P.project_sm(s.models["sm_root_monthly_v3"], one, start, 12, None, weather=w)["members"][:, 0, :], 0.5, axis=0)
        assert [int(round(v * 1000)) for v in med] == b["soil_water"]["base"]["median"][i * 12:(i + 1) * 12], cid
    # more rain never gives drier soil than less rain (v3 is monotone in rain)
    half, double = b["soil_water"]["rain_half"]["median"], b["soil_water"]["rain_double"]["median"]
    assert all(h <= d for h, d in zip(half, double) if h is not None and d is not None)
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



# ---------- expansion (roadmap): predictions, simulations, analysis, alerts, explanations, monitoring ----------

LOC = {"lat": -6.42, "lon": -79.73}


def test_cell_prediction_equals_the_projection_engine_with_real_weather():
    """A row built by the API from the cube gives the same prediction as fs_ml.project with the real weather."""
    import pandas as pd
    from fs_ml import project as P
    from app.services import prediction, state
    from app.schemas import Location
    s = state.get(); i = prediction.find_cell(Location(**LOC))
    r = client.post("/api/v1/predictions/soil-water", json={"location": LOC, "period": "2019-02"}).json()
    one = P.Cube(cells=s.cube.cells.iloc[[i]].reset_index(drop=True), dates=s.cube.dates, v={k: v[[i]] for k, v in s.cube.v.items()},
                 quarters=s.cube.quarters, ndvi=s.cube.ndvi[[i]])
    w = P.analog_weather(one, pd.Timestamp("2019-01-01"), 1, [2019])
    assert r["model"] == "sm_root_monthly_v3"
    direct = P.project_sm(s.models["sm_root_monthly_v3"], one, pd.Timestamp("2019-01-01"), 1, None, weather=w)["members"][0, 0, 0]
    assert abs(r["prediction"] - direct) < 1e-6 and r["split"] == "validation" and r["observed"] is not None


def test_feature_predictions_pick_v1_or_v3_by_their_features():
    v1 = client.post("/api/v1/predictions/soil-water", json={"features": sm_features()}).json()
    era5 = {"era5_rain_mm": 80.0, "era5_rain_mm_lag1": 40.0, "era5_rain_mm_lag2": 20.0, "era5_rain_mm_sum6": 240.0}
    v3 = client.post("/api/v1/predictions/soil-water", json={"features": sm_features(**era5)}).json()
    assert v1["model"] == "sm_root_monthly" and v3["model"] == "sm_root_monthly_v3"
    wet = client.post("/api/v1/predictions", json={"model": "sm_root_monthly_v3", "features": sm_features(**era5 | {"era5_rain_mm": 300.0})}).json()
    assert wet["prediction"] >= v3["prediction"]                  # monotone in rain
    assert v3["interval_90"]["high"] - v3["interval_90"]["low"] < v1["interval_90"]["high"] - v1["interval_90"]["low"]


def test_ndvi_complete_batch_history_confidence():
    nd = client.post("/api/v1/predictions/ndvi", json={"location": LOC, "period": "2020Q2"})
    assert nd.status_code == 200 and -1 <= nd.json()["prediction"] <= 1
    c = client.post("/api/v1/predictions/complete", json={"location": LOC, "quarter": "2024Q1"}).json()
    assert len(c["soil_water"]) == 3 and "prediction" in c["ndvi"]
    b = client.post("/api/v1/predictions/batch", json={"model": "sm_root_monthly", "items": [sm_features(), sm_features(rain_mm=-5)]}).json()
    assert len(b["results"]) == 1 and b["errors"][0]["index"] == 1
    cid = c["location"]["cell_id"]
    h = client.get(f"/api/v1/predictions/{cid}/history", params={"from": "2017-11", "to": "2018-02"}).json()
    assert [r["split"] for r in h["rows"]] == ["training", "training", "validation", "validation"]
    conf = client.get(f"/api/v1/predictions/{cid}/confidence").json()
    assert conf["historical_error"]["validation_2018_2022"]["rmse"] > 0 and conf["reliability"] in ("warning", "experimental")
    assert client.post("/api/v1/predictions/soil-water", json={"location": LOC, "period": "1990-01"}).status_code == 400
    assert client.get("/api/v1/predictions/0,0/history").status_code == 400


def test_typed_simulations_share_one_engine():
    d = client.post("/api/v1/simulations/drought", json={"location": LOC, "months": 3, "horizon": 6})
    assert d.status_code == 200, d.text
    d = d.json()
    assert d["kind"] == "drought" and "lead months [1, 2, 3]" in d["modified_inputs"][0] and d["ndvi"]["periods"][0] == "2026Q1"
    again = client.get(f"/api/v1/simulations/{d['simulation_id']}/results").json()
    assert again["scenario"]["median"] == d["scenario"]["median"]
    e = client.post("/api/v1/simulations/el-nino", json={"location": LOC}).json()
    assert e["scenario"]["analog_years"] == [1998, 2016, 2017, 2023, 2024] and any(w["code"] == "few_analogs" for w in e["warnings"])
    t = client.post("/api/v1/simulations/temperature", json={"location": LOC, "delta": 2}).json()
    assert any(w["code"] == "pet_not_recomputed" for w in t["warnings"])
    rec = client.post("/api/v1/simulations/recovery", json={"location": LOC, "drought_months": 2}).json()
    assert len(rec["periods"]) == 12 and "recovery" in rec
    cus = client.post("/api/v1/simulations/custom", json={"location": LOC, "scenario": {"t2m_delta": 2, "pet_factor": 0.8}}).json()
    assert cus["reliability_level"] == "experimental" and any(w["code"] == "inconsistent" for w in cus["warnings"])
    assert client.post("/api/v1/simulations/temperature", json={"location": LOC, "delta": 5}).status_code == 422
    assert client.post("/api/v1/simulations/drought", json={"location": LOC, "months": 6, "horizon": 3}).status_code == 422
    assert client.get("/api/v1/simulations/sim_unknown/results").status_code == 400


def test_explanations_add_up_to_the_prediction():
    p = client.post("/api/v1/predictions", json={"model": "sm_root_monthly", "features": sm_features()}).json()
    ex = client.get(f"/api/v1/explanations/{p['prediction_id']}").json()
    total = ex["base_value"] + sum(c["contribution"] for c in ex["contributions"])
    assert abs(total - p["prediction"]) < 1e-4 and abs(ex["prediction"] - p["prediction"]) < 1e-4
    assert client.get("/api/v1/explanations/pred_unknown").status_code == 400


def test_territorial_analysis_and_alerts():
    d = client.get("/api/v1/analysis/districts").json()
    assert len(d["districts"]) >= 30 and all(r["cells"] >= 1 for r in d["districts"])
    w = client.get("/api/v1/analysis/water-retention", params={"province": "Lambayeque"}).json()
    b = client.get("/api/v1/projections").json()
    ref = sorted([r for r in b["district_summary"] if r["scenario"] == "base"], key=lambda r: -r["dry_season_soil_water"])
    names = [r["district"] for r in w["districts"]]
    assert names == [r["district"] for r in ref if r["district"] in names]       # same order as the web's ranking
    assert client.get("/api/v1/analysis/vegetation", params={"scenario": "el_nino"}).status_code == 200
    r = client.get("/api/v1/analysis/drought-risk", params={"lead": 2}).json()
    assert all(0 <= x["value"] <= 1 for x in r["districts"])
    a = client.get("/api/v1/analysis/anomalies", params={"variable": "ndvi", "period": "2024Q1"}).json()
    assert a["reliability"] == "experimental" and a["districts"]
    assert client.get("/api/v1/analysis/hotspots").json()["reliability"] == "experimental"
    al = client.get("/api/v1/alerts/drought", params={"month": "2023-03"}).json()
    assert al["cells_checked"] > 1000 and 0 <= al["share_flagged"] <= 1
    assert client.get("/api/v1/alerts/vegetation", params={"quarter": "2023Q2"}).status_code == 200
    assert client.get("/api/v1/alerts/drought", params={"month": "1998-01"}).status_code == 400


def test_monitoring():
    assert client.get("/api/v1/models/health").json()["model_loaded"] is True
    m = client.get("/api/v1/models/metrics").json()
    assert "validation_2018_2022" in m["sm_root_monthly"]["metrics_by_period"]
    v = client.get("/api/v1/models/validation").json()
    assert v["sm_root_monthly"]["validation_2018_2022_criteria"][0]["criterion"] == "A"


def test_cells_outside_lambayeque_are_served_with_their_own_validation():
    from app.services import state
    c = state.get().cube.cells
    cid = c[(c.province == "outside")].cell_id.iloc[100]
    r = client.post("/api/v1/predictions/soil-water", json={"location": {"cell_id": cid}, "period": "2020-03"}).json()
    assert r["location"]["inside_lambayeque"] is False and any(w["code"] == "outside_lambayeque" for w in r["warning_details"])


def test_timeline_keeps_observed_model_and_projection_apart():
    tl = client.get("/api/v1/timeline", params=LOC).json()
    n = len(tl["months"])
    assert tl["months"][0] == "1998-01" and tl["months"][-1] == "2025-12" and len(tl["split"]) == n
    assert [(l["top_cm"], l["bottom_cm"]) for l in tl["layers"]] == [(0, 7), (7, 28), (28, 100)]
    assert all(len(l["observed"]) == n and len(l["usual_by_month"]) == 12 for l in tl["layers"])
    assert tl["layers"][1]["model_input"] is False and tl["layers"][2]["model_input"] is True
    h = client.get(f"/api/v1/predictions/{tl['location']['cell_id']}/history", params={"from": "2019-02", "to": "2019-02"}).json()["rows"][0]
    k = tl["months"].index("2019-02")
    assert tl["layers"][2]["observed"][k] == round(h["observed"], 4) and tl["model"]["predicted"][k] == round(h["predicted"], 4)
    assert tl["future"]["soil_water"]["periods"][0] == "2026-01" and len(tl["future"]["ndvi"]["periods"]) == 4
    assert client.get("/api/v1/timeline", params={"lat": 0, "lon": 0}).status_code == 400


def test_timeline_uses_the_nearest_square_just_past_the_edge():
    step = 0.017966305682390427
    edge = client.get("/api/v1/timeline", params={"lat": -383.5 * step, "lon": -4432.5 * step}).json()   # cell -4433,-384: just past the grid's edge
    assert edge["location"]["nearest"] is True and 0 < edge["location"]["distance_km"] <= 3
    far = client.get("/api/v1/timeline", params={"lat": -5.0, "lon": -81.5})
    assert far.status_code == 400 and "outside_grid" in far.json()["detail"]


def test_trends_to_2030_are_labelled_by_check_t():
    """docs/ML_TRENDS.md: the 1998-2025 trend of each variable, its extension to 2030 with a range, and check T's verdict."""
    import numpy as np
    from fs_ml import trends as T
    tl = client.get("/api/v1/timeline", params=LOC).json()
    for name in ("soil_water", "temperature", "rain", "ndvi"):
        tr = tl["trends"][name]
        assert tr["years"][0] == 1998 and tr["years"][-1] == 2025 and tr["check"]["trend_helps"] is False
        if "extension" in tr:
            e = tr["extension"]
            assert e["years"] == [2026, 2027, 2028, 2029, 2030] and all(lo <= c <= hi for lo, c, hi in zip(e["low"], e["centre"], e["high"]))
    sw = tl["trends"]["soil_water"]
    ref = T.theil_sen(np.array(sw["years"]), np.array([np.nan if v is None else v for v in sw["yearly"]], float))
    assert abs(ref["slope"] * 10 - sw["per_decade"]) < 1e-4
    b = client.get("/api/v1/projections").json()["trends"]
    assert len(b["temperature"]["per_decade"]) == len(b["soil_water"]["clear"]) == len(client.get("/api/v1/projections").json()["cells"]["x"])
