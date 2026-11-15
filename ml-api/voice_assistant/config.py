"""Configuración del asistente: todo por variables de entorno (o ml-api/.env)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # ml-api/


def _load_env_file() -> None:
    env = ROOT / ".env"
    if not env.is_file():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    assistant_name: str
    persona_path: Path | None
    persona_max_chars: int
    # LLM (Groq) — la clave vive solo en el servidor
    groq_api_key: str
    groq_model: str
    groq_timeout: float
    groq_max_retries: int
    groq_max_tokens: int
    groq_reasoning_effort: str
    # Voz
    stt_model: str
    stt_language: str
    stt_device: str
    stt_compute_type: str
    tts_engine: str
    tts_language: str
    tts_enabled: bool
    piper_voice_path: Path
    # Orquestación
    api_prefix: str
    max_tool_rounds: int
    max_audio_mb: int
    tool_result_max_chars: int


def load_settings() -> Settings:
    _load_env_file()
    voice = Path(os.getenv("PIPER_VOICE_PATH", "voice_assistant/models/es_ES-davefx-medium.onnx"))
    if not voice.is_absolute():
        voice = ROOT / voice

    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip()
    # reasoning_effort solo lo aceptan los modelos de razonamiento (gpt-oss).
    default_effort = "low" if "gpt-oss" in model else ""

    persona_raw = os.getenv("FS_PERSONA_PATH", "").strip()   # el mismo archivo que usa Sprout
    persona = None
    if persona_raw:
        p = Path(persona_raw)
        persona = p if p.is_absolute() else (ROOT / p).resolve()

    return Settings(
        assistant_name=os.getenv("ASSISTANT_NAME", "Pavo"),
        persona_path=persona,
        persona_max_chars=int(os.getenv("VOICE_PERSONA_MAX_CHARS", "4000")),
        groq_api_key=os.getenv("GROQ_API_KEY", "").strip(),
        groq_model=model,
        groq_timeout=float(os.getenv("GROQ_TIMEOUT", "45")),
        groq_max_retries=int(os.getenv("GROQ_MAX_RETRIES", "2")),
        groq_max_tokens=int(os.getenv("GROQ_MAX_TOKENS", "1024")),
        groq_reasoning_effort=os.getenv("GROQ_REASONING_EFFORT", default_effort).strip(),
        stt_model=os.getenv("STT_MODEL", "small"),
        stt_language=os.getenv("STT_LANGUAGE", "es"),
        stt_device=os.getenv("STT_DEVICE", "cpu"),
        stt_compute_type=os.getenv("STT_COMPUTE_TYPE", "int8"),
        tts_engine=os.getenv("TTS_ENGINE", "piper"),
        tts_language=os.getenv("TTS_LANGUAGE", "es"),
        tts_enabled=_bool("TTS_ENABLED", True),
        piper_voice_path=voice,
        api_prefix=os.getenv("ASSISTANT_API_PREFIX", "/api/v1").rstrip("/"),
        max_tool_rounds=int(os.getenv("ASSISTANT_MAX_TOOL_ROUNDS", "4")),
        max_audio_mb=int(os.getenv("ASSISTANT_MAX_AUDIO_MB", "15")),
        tool_result_max_chars=int(os.getenv("ASSISTANT_TOOL_RESULT_MAX_CHARS", "6000")),
    )


settings = load_settings()