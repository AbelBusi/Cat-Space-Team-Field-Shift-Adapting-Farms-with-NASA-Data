"""Voz -> texto con faster-whisper (el modelo se carga la primera vez que se usa)."""
from __future__ import annotations

import asyncio
import os
import tempfile
import threading

from .config import settings

_model = None
_lock = threading.Lock()


def is_available() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except ImportError:
        return False


def _get_model():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from faster_whisper import WhisperModel
                _model = WhisperModel(
                    settings.stt_model,
                    device=settings.stt_device,
                    compute_type=settings.stt_compute_type,
                )
    return _model


def _transcribe_sync(data: bytes, suffix: str) -> str:
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        path = tmp.name
    try:
        segments, _info = _get_model().transcribe(
            path,
            language=settings.stt_language,
            beam_size=1,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        return " ".join(seg.text.strip() for seg in segments).strip()
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


async def transcribe(data: bytes, filename: str | None = None) -> str:
    suffix = os.path.splitext(filename or "")[1] or ".webm"
    return await asyncio.to_thread(_transcribe_sync, data, suffix)