"""Sprout's voice assistant without calling any AI provider: status, the navigation tools and their facts."""
import asyncio

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
client.__enter__()


def _tool(name, args):
    from voice_assistant import tools
    return asyncio.run(tools.execute_tool(name, args, tools.FieldShiftClient(app), {}))


def test_status_lists_the_tools_and_engines():
    s = client.get("/api/v1/assistant/status").json()
    assert s["assistant_name"] == "Sprout" and {"go_to_place", "open_topic"} <= set(s["tools"])
    assert s["stt"]["language"].startswith("auto") and s["tts"]["engine"] in ("browser", "piper")


def test_go_to_place_finds_provinces_districts_and_towns():
    _, acts, ok = _tool("go_to_place", {"name": "Chiclayo"})
    assert ok and acts == [{"type": "go_to_place", "kind": "province", "name": "Chiclayo"}]
    _, acts, ok = _tool("go_to_place", {"name": "olmos"})                       # accents and case do not matter
    assert ok and acts[0]["kind"] == "district" and acts[0]["province"] == "Lambayeque"
    _, acts, ok = _tool("go_to_place", {"name": "distrito de Pomalca"})
    assert ok and acts[0]["name"] == "Pomalca"
    _, acts, ok = _tool("go_to_place", {"name": "Batán Grande"})
    assert ok and acts[0]["kind"] in ("district", "town")
    _, acts, ok = _tool("go_to_place", {"name": "Lima"})
    assert not ok and acts == []


def test_open_topic_returns_facts_computed_by_the_api():
    import json
    out, acts, ok = _tool("open_topic", {"topic": "trust"})
    d = json.loads(out)
    assert ok and acts == [{"type": "open_topic", "topic": "trust", "track": "ahead"}]
    assert d["useful_months_soil_water"] == 6 and "sm" in d["share_of_real_values_inside_the_90pct_range_2023_2025"]
    out, acts, ok = _tool("open_topic", {"topic": "spots"})
    assert ok and len(json.loads(out)["most_water_in_dry_season"]) == 3
    _, _, ok = _tool("open_topic", {"topic": "nowhere"})
    assert not ok


def test_chat_rejects_bad_input_before_calling_the_model():
    assert client.post("/api/v1/assistant/chat", json={"message": ""}).status_code == 422
    assert client.post("/api/v1/assistant/chat", json={"message": "hi", "lang": "fr"}).status_code == 422
