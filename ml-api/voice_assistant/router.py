"""Endpoints del asistente. Se monta en la app existente bajo /api/v1."""
from __future__ import annotations

import base64
import logging

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from pydantic import TypeAdapter, ValidationError

from . import speech_to_text, text_to_speech
from .assistant import Assistant
from .config import settings
from .language_model import LLMError, available_models, is_configured
from .schemas import (ChatRequest, ChatResponse, HistoryTurn, ScreenContext,
                      StatusResponse, VoiceResponse)
from .tools import TOOLS

logger = logging.getLogger("voice_assistant")
router = APIRouter(prefix="/assistant", tags=["assistant"])

_HISTORY = TypeAdapter(list[HistoryTurn])


def _llm_http_error(exc: LLMError) -> HTTPException:
    headers = {"Retry-After": exc.retry_after} if exc.retry_after else None
    return HTTPException(status_code=exc.status_code, detail=str(exc), headers=headers)


async def _answer(request: Request, message: str, context, history, speak: bool) -> dict:
    try:
        result = await Assistant(request.app).reply(message, context, history)
    except LLMError as exc:
        raise _llm_http_error(exc)

    audio_b64 = audio_mime = speak_error = None
    if speak:
        try:
            wav = await text_to_speech.synthesize(result.text)
            audio_b64, audio_mime = base64.b64encode(wav).decode("ascii"), "audio/wav"
        except Exception as exc:  # la voz es opcional: el texto siempre se devuelve
            logger.warning("TTS falló: %s", exc)
            speak_error = str(exc)[:200]
    return {"text": result.text, "mood": result.modd, "actions": result.actions, "tools_used": result.tools_used,
            "audio_base64": audio_b64, "audio_mime": audio_mime, "speak_error": speak_error}


@router.get("/status", response_model=StatusResponse)
async def status(check: bool = Query(False, description="true = probar la conexión real con Groq")) -> StatusResponse:
    llm: dict = {"provider": "groq", "model": settings.groq_model, "configured": is_configured(),
                 "reachable": None, "model_available": None}
    if check and is_configured():
        try:
            ids = await available_models()
            llm["reachable"] = True
            llm["model_available"] = settings.groq_model in ids
        except LLMError as exc:
            llm["reachable"] = False
            llm["error"] = str(exc)
    stt = {"available": speech_to_text.is_available(), "model": settings.stt_model, "language": settings.stt_language}
    tts = {"available": text_to_speech.is_available(), "engine": settings.tts_engine,
           "voice_file": str(settings.piper_voice_path), "voice_found": text_to_speech.voice_file_found()}
    llm_ok = llm["configured"] and (not check or (llm["reachable"] and llm["model_available"]))
    return StatusResponse(ok=bool(llm_ok and stt["available"]), assistant_name=settings.assistant_name,
                          llm=llm, stt=stt, tts=tts, tools=list(TOOLS))


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(body: ChatRequest, request: Request) -> ChatResponse:
    data = await _answer(request, body.message, body.context, body.history, body.speak)
    return ChatResponse(**data)


@router.post("/voice", response_model=VoiceResponse)
async def voice_endpoint(
    request: Request,
    audio: UploadFile = File(...),
    context: str | None = Form(None, description="JSON de ScreenContext"),
    history: str | None = Form(None, description="JSON: lista de {role, content}"),
    speak: bool = Form(True),
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

    try:
        transcript = await speech_to_text.transcribe(data, audio.filename)
    except ImportError:
        raise HTTPException(status_code=503, detail="faster-whisper no está instalado.")
    except Exception:  # noqa: BLE001
        logger.exception("Falló la transcripción")
        raise HTTPException(status_code=500, detail="No se pudo transcribir el audio.")

    if not transcript:
        fallback = "No te escuché bien. ¿Puedes repetirlo?"
        audio_b64 = audio_mime = speak_error = None
        if speak:
            try:
                audio_b64 = base64.b64encode(await text_to_speech.synthesize(fallback)).decode("ascii")
                audio_mime = "audio/wav"
            except Exception as exc:  # noqa: BLE001
                speak_error = str(exc)[:200]
        return VoiceResponse(transcript="", text=fallback, audio_base64=audio_b64, audio_mime=audio_mime, speak_error=speak_error)

    out = await _answer(request, transcript, ctx, hist, speak)
    return VoiceResponse(transcript=transcript, **out)