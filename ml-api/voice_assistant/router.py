"""Endpoints del asistente. Se monta en la app existente bajo /api/v1."""
from __future__ import annotations

import base64
import logging

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, Response, UploadFile
from pydantic import TypeAdapter, ValidationError

from . import speech_to_text, text_to_speech
from .assistant import Assistant
from .config import settings
from .language_model import LLMError, available_models, is_configured
from .schemas import (ChatRequest, ChatResponse, HistoryTurn, ScreenContext, SpeakRequest,
                      StatusResponse, VoiceResponse)
from .tools import TOOLS

logger = logging.getLogger("voice_assistant")
router = APIRouter(prefix="/assistant", tags=["assistant"])

_HISTORY = TypeAdapter(list[HistoryTurn])


def _llm_http_error(exc: LLMError) -> HTTPException:
    headers = {"Retry-After": exc.retry_after} if exc.retry_after else None
    return HTTPException(status_code=exc.status_code, detail=str(exc), headers=headers)


FALLBACK = {"es": "No te escuché bien. ¿Me lo repites?", "en": "I did not hear you well. Could you say it again?"}


async def _voice(text: str, lang: str, speak: bool) -> dict:
    """Audio del servidor (Piper) si está activo; si no, la web lo dice con la voz del navegador."""
    out = {"audio_base64": None, "audio_mime": None, "speak_error": None}
    if not speak:
        return out
    try:
        wav = await text_to_speech.synthesize(text, lang)
        if wav:
            out.update(audio_base64=base64.b64encode(wav).decode("ascii"), audio_mime="audio/wav")
    except Exception as exc:  # la voz es opcional: el texto siempre se devuelve
        logger.warning("TTS falló: %s", exc)
        out["speak_error"] = str(exc)[:200]
    return out


async def _answer(request: Request, message: str, context, history, speak: bool, lang: str) -> dict:
    try:
        result = await Assistant(request.app).reply(message, context, history, lang)
    except LLMError as exc:
        raise _llm_http_error(exc)
    return {"text": result.text, "mood": result.mood, "actions": result.actions, "tools_used": result.tools_used,
            "lang": lang, **(await _voice(result.text, lang, speak))}


_SPOKEN: dict[tuple[str, str], bytes] = {}   # Sprout repeats its guide lines: keep the last ones ready


@router.post("/speak", response_class=Response, responses={200: {"content": {"audio/wav": {}}}})
async def speak(body: SpeakRequest) -> Response:
    """Sprout's voice for any line it says (guide lines included). 204 when the browser should speak instead."""
    key = (body.lang, body.text)
    wav = _SPOKEN.get(key)
    if wav is None:
        try:
            wav = await text_to_speech.synthesize(body.text, body.lang)
        except Exception as exc:  # noqa: BLE001
            logger.warning("TTS falló: %s", exc)
            raise HTTPException(status_code=503, detail="Sprout's voice is not available on the server.")
        if not wav:
            return Response(status_code=204)
        if len(_SPOKEN) > 300:
            _SPOKEN.pop(next(iter(_SPOKEN)))
        _SPOKEN[key] = wav
    return Response(content=wav, media_type="audio/wav", headers={"Cache-Control": "public, max-age=86400"})


@router.get("/status", response_model=StatusResponse)
async def status(check: bool = Query(False, description="true = probar la conexión real con Groq")) -> StatusResponse:
    llm: dict = {"base_url": settings.llm_base_url, "model": settings.llm_model, "configured": is_configured(),
                 "reachable": None, "model_available": None}
    if check and is_configured():
        try:
            ids = await available_models()
            llm["reachable"] = True
            llm["model_available"] = settings.llm_model in ids
        except LLMError as exc:
            llm["reachable"] = False
            llm["error"] = str(exc)
    stt = {"available": speech_to_text.is_available(), "engine": speech_to_text.engine(),
           "model": settings.stt_cloud_model if settings.stt_engine == "groq" else settings.stt_model, "language": "auto (es / en)"}
    tts = {"available": text_to_speech.is_available(), "engine": text_to_speech.engine(), "pitch": settings.tts_pitch,
           "voices": text_to_speech.voice_files() if settings.tts_engine == "piper" else "the browser's own voice, high and soft"}
    llm_ok = llm["configured"] and (not check or (llm["reachable"] and llm["model_available"]))
    return StatusResponse(ok=bool(llm_ok and stt["available"]), assistant_name=settings.assistant_name,
                          llm=llm, stt=stt, tts=tts, tools=list(TOOLS))


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(body: ChatRequest, request: Request) -> ChatResponse:
    data = await _answer(request, body.message, body.context, body.history, body.speak, body.lang)
    return ChatResponse(**data)


@router.post("/voice", response_model=VoiceResponse)
async def voice_endpoint(
    request: Request,
    audio: UploadFile = File(...),
    context: str | None = Form(None, description="JSON de ScreenContext"),
    history: str | None = Form(None, description="JSON: lista de {role, content}"),
    speak: bool = Form(True),
    lang: str = Form("es", description="idioma de la web: es o en (si hablas en el otro, Sprout te responde en ese)"),
) -> VoiceResponse:
    try:
        ctx = ScreenContext.model_validate_json(context) if context else None
        hist = _HISTORY.validate_json(history) if history else []
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=f"context/history inválido: {exc.errors()[:2]}")

    data = await audio.read()
    if not data:
        raise HTTPException(status_code=400, detail="El audio está vacío.")
    if len(data) > settings.max_audio_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"El audio supera {settings.max_audio_mb} MB.")

    lang = lang if lang in ("es", "en") else "es"
    try:
        transcript, spoken = await speech_to_text.transcribe(data, audio.filename)
    except LLMError as exc:
        raise _llm_http_error(exc)
    except ImportError:
        raise HTTPException(status_code=503, detail="faster-whisper no está instalado (STT_ENGINE=local).")
    except Exception:  # noqa: BLE001
        logger.exception("Falló la transcripción")
        raise HTTPException(status_code=500, detail="No se pudo transcribir el audio.")
    if spoken in ("es", "en"):
        lang = spoken                      # se responde en el idioma en que habló el usuario

    if not transcript:
        text = FALLBACK[lang]
        return VoiceResponse(transcript="", text=text, mood="shy", lang=lang, **(await _voice(text, lang, speak)))

    out = await _answer(request, transcript, ctx, hist, speak, lang)
    return VoiceResponse(transcript=transcript, **out)
