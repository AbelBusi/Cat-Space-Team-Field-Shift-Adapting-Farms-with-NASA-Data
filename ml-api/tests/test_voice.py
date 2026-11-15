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


def test_speak_returns_sprouts_voice_or_tells_the_browser_to_speak():
    import io
    import wave
    r = client.post("/api/v1/assistant/speak", json={"text": "Miau, hola. Soy Sprout.", "lang": "es"})
    assert r.status_code in (200, 204, 503)
    if r.status_code == 200:
        w = wave.open(io.BytesIO(r.content))
        assert r.headers["content-type"] == "audio/wav" and w.getnframes() / w.getframerate() > 0.5
    assert client.post("/api/v1/assistant/speak", json={"text": "", "lang": "es"}).status_code == 422


def test_intents_become_navigation_even_when_the_model_skips_a_step():
    from voice_assistant.assistant import _complete_navigation, _default_choices, _rescue_choices
    # "I want to save water": the model only set the priorities -> the priorities screen opens and its card is pointed at
    acts = _complete_navigation([{"type": "set_view", "priorities": {"water": 3}}])
    assert acts[-1] == {"type": "open_topic", "topic": "prio", "track": "today"} and acts[0]["focus"] == "priorities"
    # "I worry about the heat": signal -> the satellites screen
    assert _complete_navigation([{"type": "set_view", "signal": "heat"}])[-1]["topic"] == "signals"
    # an explicit topic is kept as it is
    kept = _complete_navigation([{"type": "open_topic", "topic": "trends", "track": "ahead"}, {"type": "set_view", "signal": "rain"}])
    assert [a["topic"] for a in kept if a["type"] == "open_topic"] == ["trends"]
    # next steps: written by the model as text, or by screen in the reply's language
    assert _rescue_choices('Listo. [ "Ver la lluvia", "Ver El Niño" ]') == ("Listo.", ["Ver la lluvia", "Ver El Niño"])
    en = _default_choices([{"type": "open_topic", "topic": "whatif", "track": "ahead"}], "en")
    assert en[-1]["type"] == "choices" and en[-1]["items"][0].startswith("And with half")
