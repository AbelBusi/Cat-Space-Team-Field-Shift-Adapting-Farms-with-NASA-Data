"""Voz -> texto. Dos motores:
- "groq" (por defecto): Whisper en la nube con la misma clave del chat. Sin descargas, rápido, detecta el idioma.
- "local": faster-whisper en esta máquina (el modelo se descarga la primera vez y se queda en caché).
Devuelve (texto, idioma detectado "es"/"en"/…, o None)."""
from __future__ import annotations

import asyncio
import os
import tempfile
import threading

from .config import settings
from .language_model import is_configured, post

_model = None
_lock = threading.Lock()


def _local_available() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except ImportError:
        return False


def is_available() -> bool:
    return is_configured() if settings.stt_engine == "groq" else _local_available()


def engine() -> str:
    return settings.stt_engine


def _get_model():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from faster_whisper import WhisperModel
                _model = WhisperModel(settings.stt_model, device=settings.stt_device, compute_type=settings.stt_compute_type)
    return _model


def _transcribe_local(data: bytes, suffix: str, language: str | None) -> tuple[str, str | None]:
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        path = tmp.name
    try:
        segments, info = _get_model().transcribe(path, language=language, beam_size=1, vad_filter=True, condition_on_previous_text=False)
        text = " ".join(seg.text.strip() for seg in segments).strip()
        return text, getattr(info, "language", language)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


_LANG_NAMES = {"spanish": "es", "english": "en"}


async def transcribe(data: bytes, filename: str | None = None, language: str | None = None) -> tuple[str, str | None]:
    """language=None deja que Whisper detecte si hablas en español o en inglés."""
    suffix = os.path.splitext(filename or "")[1] or ".webm"
    if settings.stt_engine == "local":
        return await asyncio.to_thread(_transcribe_local, data, suffix, language)
    form = {"model": settings.stt_cloud_model, "response_format": "verbose_json", "temperature": "0"}
    if language:
        form["language"] = language
    out = await post("/audio/transcriptions", files={"file": (f"voice{suffix}", data)}, data=form)
    lang = (out.get("language") or "").lower()
    return (out.get("text") or "").strip(), _LANG_NAMES.get(lang, lang[:2] or None)
