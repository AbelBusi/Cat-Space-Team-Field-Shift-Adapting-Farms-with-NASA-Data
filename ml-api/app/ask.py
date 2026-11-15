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
    """Add the tested model's projections for the user's cell, and the full result of a simulation or the explanation
    of a prediction when the web sends their ids, so Sprout interprets real numbers."""
    from .services import projections, state as st
    ctx = dict(context or {})
    lat, lon = ctx.get("lat"), ctx.get("lon")
    if st.STATE is not None and ctx.get("simulation_id"):
        from .services.scenario_engine import RESULTS
        sim = RESULTS.get(ctx["simulation_id"])
        if sim:
            ctx["simulation_result"] = {k: sim[k] for k in ("kind", "modified_inputs", "periods", "baseline", "scenario", "comparison", "ndvi",
                                                             "reliability_level", "warnings", "interpretation") if k in sim}
    if st.STATE is not None and ctx.get("prediction_id"):
        from .services import explanations
        try:
            ctx["prediction_explanation"] = explanations.by_id(ctx["prediction_id"])
        except LookupError:
            pass
    if st.STATE is not None and isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
        from .schemas import Location
        try:
            proj = {}
            for scen, note in (("base", "a normal year (the weather of each past year 1998-2025)"),
                               ("el_nino", "only the coastal El Nino years 1998, 2016, 2017, 2023, 2024 (5 years, less sure)"),
                               ("drought_feb_mar", "a normal year with no rain in Feb and Mar")):
                p = projections.projection_at(Location(lat=lat, lon=lon), "soil_water", scen)
                proj[scen] = {"what": note, "months": p["periods"][:6], "median": p["median"][:6],
                              **({"low_90": p["low_90"][:6], "high_90": p["high_90"][:6]} if p["low_90"] else {})}
            proj["usual_1998_2025"] = p["usual"][:6]
            proj["note"] = "Field Shift model, root-zone soil water 28-100 cm in m3/m3, from Dec 2025; useful for about 6 months"
            ctx["model_projection_soil_water"] = proj
        except (LookupError, ValueError):
            pass
    return ctx


def answer(question: str, lang: str, context: dict, history: list | None = None) -> str:
    if not settings.llm_base_url or not settings.llm_model:
        raise AskUnavailable("no AI model configured (LLM_BASE_URL, LLM_MODEL)")
    ctx = enrich(context)
    messages = [
        {"role": "system", "content": persona()},
        *({"role": h.role, "content": h.content} for h in (history or [])),
        {"role": "user", "content": f"lang: {lang}\ncontext (what the user sees, JSON):\n{json.dumps(ctx, ensure_ascii=False, default=str)}\n\nquestion: {question}"},
    ]
    payload = {"model": settings.llm_model, "messages": messages, "temperature": 0.4, "max_tokens": 900}
    if settings.llm_reasoning_effort:
        payload["reasoning_effort"] = settings.llm_reasoning_effort
    body = json.dumps(payload).encode()
    # A named client: some providers (Cloudflare-fronted, e.g. Groq) refuse Python's default user agent with 403
    headers = {"Content-Type": "application/json", "User-Agent": "field-shift-ml-api/0.1"}
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"
    req = urllib.request.Request(settings.llm_base_url.rstrip("/") + "/chat/completions", data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=settings.llm_timeout) as r:
            data = json.loads(r.read())
        return data["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        log.warning("AI model did not answer: HTTP %s %s", e.code, e.read()[:300])
        raise AskUnavailable("the AI model did not answer") from e
    except (urllib.error.URLError, TimeoutError, KeyError, IndexError, json.JSONDecodeError) as e:
        log.warning("AI model did not answer: %s", e)
        raise AskUnavailable("the AI model did not answer") from e
