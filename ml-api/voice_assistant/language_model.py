"""Cliente del modelo de lenguaje: cualquier endpoint compatible con OpenAI (Groq por defecto), con llamadas a
herramientas. Usa httpx (ya instalado), así que no hace falta el SDK de Groq."""
from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from .config import settings

logger = logging.getLogger("voice_assistant.llm")


class LLMError(RuntimeError):
    """Error del proveedor ya traducido a algo que el router puede devolver (sin la clave ni detalles internos)."""

    def __init__(self, kind: str, message: str, status_code: int = 503, retry_after: str | None = None):
        super().__init__(message)
        self.kind = kind
        self.status_code = status_code
        self.retry_after = retry_after


def is_configured() -> bool:
    return bool(settings.llm_api_key and settings.llm_base_url)


def _headers() -> dict:
    if not is_configured():
        raise LLMError("not_configured", "Falta la clave del modelo en el servidor (LLM_API_KEY en ml-api/.env).", 503)
    return {"Authorization": f"Bearer {settings.llm_api_key}", "User-Agent": "field-shift-ml-api/0.1"}


def _translate(resp: httpx.Response) -> LLMError:
    code = resp.status_code
    if code in (401, 403):
        return LLMError("auth", "El proveedor rechazó la clave: revisa LLM_API_KEY.", 502)
    if code == 429:
        return LLMError("rate_limit", "Se alcanzó el límite de solicitudes. Intenta de nuevo en unos segundos.", 429, resp.headers.get("retry-after"))
    if code == 404:
        return LLMError("model", f"El modelo '{settings.llm_model}' no existe o no está disponible.", 502)
    logger.warning("LLM %s: %s", code, resp.text[:300])
    return LLMError("upstream", f"El proveedor respondió con un error ({code}).", 502)


async def post(path: str, *, json: dict | None = None, files: dict | None = None, data: dict | None = None, _retry: bool = True) -> dict:
    try:
        async with httpx.AsyncClient(timeout=settings.llm_timeout) as http:
            resp = await http.post(f"{settings.llm_base_url}{path}", headers=_headers(), json=json, files=files, data=data)
    except httpx.TimeoutException as exc:
        raise LLMError("timeout", "El modelo tardó demasiado en responder.", 504) from exc
    except httpx.HTTPError as exc:
        raise LLMError("connection", "No se pudo conectar con el modelo. Revisa la conexión a internet.", 503) from exc
    if resp.status_code == 429 and _retry:
        # free tiers limit tokens per minute: when the provider asks for a short wait, wait once and try again
        try:
            wait = float(resp.headers.get("retry-after", "0"))
        except ValueError:
            wait = 0
        if 0 < wait <= 12:
            import asyncio
            await asyncio.sleep(wait)
            return await post(path, json=json, files=files, data=data, _retry=False)
    if resp.status_code >= 400:
        if resp.status_code == 400 and "tool_use_failed" in resp.text:
            raise LLMError("tool_use_failed", "tool_use_failed", 502)
        raise _translate(resp)
    return resp.json()


_THINK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def strip_think(text: str) -> str:
    return _THINK.sub("", text or "").strip()


async def chat(messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None, tool_choice: str = "auto") -> dict[str, Any]:
    """Una llamada al modelo. Devuelve {"content": str, "tool_calls": [formato OpenAI]}."""
    body: dict[str, Any] = {"model": settings.llm_model, "messages": messages, "temperature": 0.3,
                            "max_completion_tokens": settings.llm_max_tokens}
    if settings.llm_reasoning_effort:
        body["reasoning_effort"] = settings.llm_reasoning_effort
    if tools:
        body["tools"], body["tool_choice"] = tools, tool_choice
    for attempt in range(3):
        try:
            data = await post("/chat/completions", json=body)
            break
        except LLMError as exc:
            fb = settings.llm_fallback_model
            if exc.kind == "rate_limit" and fb and body["model"] != fb:
                logger.info("rate limit on %s, using %s", body["model"], fb)
                body["model"] = fb
                if "gpt-oss" not in fb:
                    body.pop("reasoning_effort", None)
                continue
            # A veces el modelo escribe una llamada a herramienta mal formada: un reintento suele bastar.
            if exc.kind == "tool_use_failed" and attempt == 0:
                logger.warning("tool_use_failed, reintentando una vez")
                continue
            if exc.kind == "tool_use_failed":
                raise LLMError("bad_request", "El modelo no pudo usar sus herramientas.", 502) from exc
            raise
    msg = data["choices"][0]["message"]
    calls = [{"id": tc["id"], "type": "function",
              "function": {"name": tc["function"]["name"], "arguments": tc["function"].get("arguments") or "{}"}}
             for tc in (msg.get("tool_calls") or [])]
    return {"content": strip_think(msg.get("content") or ""), "tool_calls": calls}


async def available_models() -> list[str]:
    try:
        async with httpx.AsyncClient(timeout=settings.llm_timeout) as http:
            resp = await http.get(f"{settings.llm_base_url}/models", headers=_headers())
    except httpx.HTTPError as exc:
        raise LLMError("connection", "No se pudo conectar con el modelo.", 503) from exc
    if resp.status_code >= 400:
        raise _translate(resp)
    return [m["id"] for m in resp.json().get("data", [])]
