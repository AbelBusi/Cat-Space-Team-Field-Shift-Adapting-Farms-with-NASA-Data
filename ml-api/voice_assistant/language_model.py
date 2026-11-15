"""Cliente de Groq (SDK oficial `groq`). Aquí vive toda la comunicación con el proveedor LLM."""
from __future__ import annotations

import logging
import re
from typing import Any

import groq
from groq import AsyncGroq

from .config import settings

logger = logging.getLogger("voice_assistant.llm")


class LLMError(RuntimeError):
    """Error del proveedor LLM ya traducido a algo que el router puede devolver."""

    def __init__(self, kind: str, message: str, status_code: int = 503, retry_after: str | None = None):
        super().__init__(message)
        self.kind = kind
        self.status_code = status_code
        self.retry_after = retry_after


_client: AsyncGroq | None = None


def is_configured() -> bool:
    return bool(settings.groq_api_key)


def _get_client() -> AsyncGroq:
    global _client
    if not settings.groq_api_key:
        raise LLMError("not_configured", "Falta GROQ_API_KEY en el servidor (ml-api/.env).", 503)
    if _client is None:
        _client = AsyncGroq(
            api_key=settings.groq_api_key,
            timeout=settings.groq_timeout,
            max_retries=settings.groq_max_retries,
        )
    return _client


def _translate(exc: Exception) -> LLMError:
    """Convierte excepciones del SDK en LLMError (sin filtrar la clave ni detalles internos)."""
    if isinstance(exc, (groq.AuthenticationError, groq.PermissionDeniedError)):
        return LLMError("auth", "Groq rechazó la clave API: GROQ_API_KEY es inválida o no tiene permisos.", 502)
    if isinstance(exc, groq.RateLimitError):
        retry = None
        try:
            retry = exc.response.headers.get("retry-after")
        except Exception:  # noqa: BLE001
            pass
        return LLMError("rate_limit", "Se alcanzó el límite de solicitudes de Groq. Intenta de nuevo en unos segundos.", 429, retry)
    if isinstance(exc, groq.APITimeoutError):  # subclase de APIConnectionError: va primero
        return LLMError("timeout", "Groq tardó demasiado en responder.", 504)
    if isinstance(exc, groq.APIConnectionError):
        return LLMError("connection", "No se pudo conectar con Groq. Revisa la conexión a internet.", 503)
    if isinstance(exc, groq.NotFoundError):
        return LLMError("model", f"El modelo '{settings.groq_model}' no existe o no está disponible para tu cuenta.", 502)
    if isinstance(exc, groq.BadRequestError):
        logger.warning("Groq 400: %s", str(exc)[:300])
        return LLMError("bad_request", "Groq rechazó la solicitud del asistente.", 502)
    if isinstance(exc, groq.APIStatusError):
        logger.warning("Groq %s: %s", exc.status_code, str(exc)[:300])
        return LLMError("upstream", f"Groq respondió con un error ({exc.status_code}).", 502)
    logger.exception("Error inesperado del cliente Groq")
    return LLMError("unknown", "Error inesperado al consultar el modelo de lenguaje.", 502)


_THINK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def strip_think(text: str) -> str:
    return _THINK.sub("", text or "").strip()


async def chat(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str = "auto",
) -> dict[str, Any]:
    """Una llamada al modelo. Devuelve {"content": str, "tool_calls": [formato OpenAI]}."""
    client = _get_client()
    kwargs: dict[str, Any] = {
        "model": settings.groq_model,
        "messages": messages,
        "temperature": 0.2,
        "max_completion_tokens": settings.groq_max_tokens,
    }
    if settings.groq_reasoning_effort:
        kwargs["reasoning_effort"] = settings.groq_reasoning_effort
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = tool_choice

    resp = None
    for attempt in range(2):
        try:
            resp = await client.chat.completions.create(**kwargs)
            break
        except groq.BadRequestError as exc:
            # Los modelos a veces generan una llamada a herramienta mal formada: un reintento suele bastar.
            if attempt == 0 and "tool_use_failed" in str(exc):
                logger.warning("tool_use_failed, reintentando una vez")
                continue
            raise _translate(exc) from exc
        except groq.GroqError as exc:
            raise _translate(exc) from exc

    msg = resp.choices[0].message
    calls = [
        {
            "id": tc.id,
            "type": "function",
            "function": {"name": tc.function.name, "arguments": tc.function.arguments or "{}"},
        }
        for tc in (msg.tool_calls or [])
    ]
    return {"content": strip_think(msg.content or ""), "tool_calls": calls}


async def available_models() -> list[str]:
    client = _get_client()
    try:
        result = await client.models.list()
    except groq.GroqError as exc:
        raise _translate(exc) from exc
    return [m.id for m in result.data]