"""Texto -> voz con Piper. Devuelve WAV en bytes."""
from __future__ import annotations

import asyncio
import io
import threading
import wave

from .config import settings

_voice = None
_lock = threading.Lock()


def is_available() -> bool:
    try:
        import piper  # noqa: F401
        return True
    except ImportError:
        return False


def voice_file_found() -> bool:
    return settings.piper_voice_path.is_file()


def _get_voice():
    global _voice
    if _voice is None:
        with _lock:
            if _voice is None:
                from piper import PiperVoice
                if not voice_file_found():
                    raise FileNotFoundError(f"No existe la voz de Piper: {settings.piper_voice_path}")
                _voice = PiperVoice.load(str(settings.piper_voice_path))
    return _voice


def _synthesize_sync(text: str) -> bytes:
    voice = _get_voice()
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        if hasattr(voice, "synthesize_wav"):   # piper-tts >= 1.3
            voice.synthesize_wav(text, wav)
        else:                                  # piper-tts 1.2
            voice.synthesize(text, wav)
    return buffer.getvalue()


async def synthesize(text: str) -> bytes:
    if not settings.tts_enabled:
        raise RuntimeError("TTS desactivado (TTS_ENABLED=false)")
    return await asyncio.to_thread(_synthesize_sync, text)