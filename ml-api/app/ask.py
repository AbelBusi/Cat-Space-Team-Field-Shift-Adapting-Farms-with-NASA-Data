"""Sprout's open questions: an AI chat model behind the API, so no key ever reaches the browser.

Any OpenAI-compatible chat endpoint works (one code path): Ollama on your own machine (free, the default), or a hosted
service with a free tier (Groq, OpenRouter ':free' models, Google Gemini's OpenAI-compatible endpoint), or a paid one.
The persona is docs/SPROUT_PERSONA.md; the web sends what is on screen as `context`, and the API adds the model's
projection for that cell, so the answer interprets real numbers instead of inventing them."""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from .config import settings

log = logging.getLogger("ml-api")


class AskUnavailable(RuntimeError):
    pass


def persona() -> str:
    text = settings.persona_path.read_text(encoding="utf-8")
    return text.split("\n---\n", 1)[-1].strip()       # only the part below the line is the prompt


def enrich(context: dict) -> dict:
    """Add the tested model's projection for the user's cell (soil water, normal year), when there is one."""
    from . import service
    ctx = dict(context or {})
    lat, lon = ctx.get("lat"), ctx.get("lon")
    if service.STATE is not None and isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
        from .schemas import Location
        try:
            p = service.projection_at(Location(lat=lat, lon=lon), "soil_water", "base")
            ctx["model_projection_soil_water_28_100cm_m3m3"] = {
                "start": "last observed month 2025-12", "months": p["periods"][:6], "median": p["median"][:6],
                "low_90": p["low_90"][:6], "high_90": p["high_90"][:6], "usual_1998_2025": p["usual"][:6],
                "note": "normal-year projection from the past years' weather; useful for about 6 months"}
        except (LookupError, ValueError):
            pass
    return ctx


def answer(question: str, lang: str, context: dict) -> str:
    if not settings.llm_base_url or not settings.llm_model:
        raise AskUnavailable("no AI model configured (LLM_BASE_URL, LLM_MODEL)")
    ctx = enrich(context)
    messages = [
        {"role": "system", "content": persona()},
        {"role": "user", "content": f"lang: {lang}\ncontext (what the user sees, JSON):\n{json.dumps(ctx, ensure_ascii=False, default=str)}\n\nquestion: {question}"},
    ]
    body = json.dumps({"model": settings.llm_model, "messages": messages, "temperature": 0.4, "max_tokens": 350}).encode()
    headers = {"Content-Type": "application/json"}
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"
    req = urllib.request.Request(settings.llm_base_url.rstrip("/") + "/chat/completions", data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=settings.llm_timeout) as r:
            data = json.loads(r.read())
        return data["choices"][0]["message"]["content"].strip()
    except (urllib.error.URLError, TimeoutError, KeyError, IndexError, json.JSONDecodeError) as e:
        log.warning("AI model did not answer: %s", e)
        raise AskUnavailable("the AI model did not answer") from e
