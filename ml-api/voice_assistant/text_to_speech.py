"""Texto -> voz.
- "browser" (por defecto): el servidor no genera audio; la web habla con la voz del navegador, con el tono alto y
  suave de un gatito (Web Speech API). Sin descargas, en español e inglés.
- "piper": voz local en el servidor (piper-tts + un archivo .onnx por idioma). Para que suene a gatito se sube el tono:
  el WAV se marca con una frecuencia de muestreo más alta (TTS_PITCH, 1.3 = unos 4,5 semitonos más agudo y un poco
  más rápido), sin procesar el audio."""
from __future__ import annotations

import asyncio
import io
import threading
import wave

from .config import settings

_voices: dict = {}
_lock = threading.Lock()


def engine() -> str:
    return settings.tts_engine


def is_available() -> bool:
    if settings.tts_engine != "piper":
        return True
    try:
        import piper  # noqa: F401
        return True
    except ImportError:
        return False


def voice_files() -> dict:
    return {lang: {"path": str(p), "found": p.is_file()} for lang, p in settings.piper_voices.items()}


def _get_voice(lang: str):
    path = settings.piper_voices.get(lang) or settings.piper_voices["es"]
    if path not in _voices:
        with _lock:
            if path not in _voices:
                from piper import PiperVoice
                if not path.is_file():
                    raise FileNotFoundError(f"No existe la voz de Piper: {path}")
                _voices[path] = PiperVoice.load(str(path))
    return _voices[path]


def _synthesize_sync(text: str, lang: str) -> bytes:
    voice = _get_voice(lang)
    raw = io.BytesIO()
    with wave.open(raw, "wb") as wav:
        if hasattr(voice, "synthesize_wav"):   # piper-tts >= 1.3
            voice.synthesize_wav(text, wav)
        else:                                  # piper-tts 1.2
            voice.synthesize(text, wav)
    raw.seek(0)
    with wave.open(raw, "rb") as src:          # tono de gatito: misma muestra, reproducida más rápido
        params, frames = src.getparams(), src.readframes(src.getnframes())
    out = io.BytesIO()
    with wave.open(out, "wb") as dst:
        dst.setparams(params)
        dst.setframerate(int(params.framerate * settings.tts_pitch))
        dst.writeframes(frames)
    return out.getvalue()


async def synthesize(text: str, lang: str = "es") -> bytes | None:
    """WAV en bytes, o None si la voz la pone el navegador."""
    if not settings.tts_enabled or settings.tts_engine != "piper":
        return None
    return await asyncio.to_thread(_synthesize_sync, text, lang)
