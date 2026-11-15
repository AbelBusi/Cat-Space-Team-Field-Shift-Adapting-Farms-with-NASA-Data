"""Configuración del asistente de voz: todo por variables de entorno (o ml-api/.env).

Por defecto reutiliza la conexión del chat de Sprout (LLM_BASE_URL, LLM_API_KEY, LLM_MODEL): una sola clave para todo.
Las variables VOICE_* / GROQ_* solo hacen falta para usar otro proveedor o modelo en la voz."""
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


def _path(raw: str) -> Path:
    p = Path(raw)
    return p if p.is_absolute() else (ROOT / p).resolve()


def _first(*names: str, default: str = "") -> str:
    for n in names:
        v = os.getenv(n, "").strip()
        if v:
            return v
    return default


@dataclass(frozen=True)
class Settings:
    assistant_name: str
    persona_path: Path | None
    persona_max_chars: int
    # LLM (OpenAI-compatible: Groq por defecto). La clave vive solo en el servidor.
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    llm_fallback_model: str     # used when the first model hits its per-minute limit (free tiers: 8,000 tokens/min each)
    llm_timeout: float
    llm_max_tokens: int
    llm_reasoning_effort: str
    # Voz -> texto: "groq" (Whisper en la nube, sin descargas) o "local" (faster-whisper)
    stt_engine: str
    stt_model: str
    stt_cloud_model: str
    stt_device: str
    stt_compute_type: str
    # Texto -> voz: "browser" (la voz del navegador, con tono alto de gatito) o "piper" (local, en el servidor)
    tts_engine: str
    tts_enabled: bool
    piper_voices: dict
    tts_pitch: float
    # Datos para llevar al usuario a lugares y temas de la web
    places_dir: Path
    # Orquestación
    api_prefix: str
    max_tool_rounds: int
    max_audio_mb: int
    tool_result_max_chars: int


def load_settings() -> Settings:
    _load_env_file()
    model = _first("VOICE_LLM_MODEL", "GROQ_MODEL", "LLM_MODEL", default="openai/gpt-oss-20b")
    persona_raw = os.getenv("FS_PERSONA_PATH", "../docs/SPROUT_PERSONA.md").strip()
    return Settings(
        assistant_name=os.getenv("ASSISTANT_NAME", "Sprout"),
        persona_path=_path(persona_raw) if persona_raw else None,
        persona_max_chars=int(os.getenv("VOICE_PERSONA_MAX_CHARS", "0")),   # the system prompt already carries Sprout
        llm_base_url=_first("VOICE_LLM_BASE_URL", "LLM_BASE_URL", default="https://api.groq.com/openai/v1").rstrip("/"),
        llm_api_key=_first("VOICE_LLM_API_KEY", "GROQ_API_KEY", "LLM_API_KEY"),
        llm_model=model,
        llm_fallback_model=_first("VOICE_LLM_FALLBACK_MODEL", "LLM_MODEL", default=""),
        llm_timeout=float(os.getenv("VOICE_LLM_TIMEOUT", "45")),
        llm_max_tokens=int(os.getenv("VOICE_LLM_MAX_TOKENS", "500")),
        llm_reasoning_effort=_first("VOICE_REASONING_EFFORT", "LLM_REASONING_EFFORT", default="low" if "gpt-oss" in model else ""),
        stt_engine=os.getenv("STT_ENGINE", "groq").strip().lower(),
        stt_model=os.getenv("STT_MODEL", "small"),
        stt_cloud_model=os.getenv("STT_CLOUD_MODEL", "whisper-large-v3-turbo"),
        stt_device=os.getenv("STT_DEVICE", "cpu"),
        stt_compute_type=os.getenv("STT_COMPUTE_TYPE", "int8"),
        tts_engine=os.getenv("TTS_ENGINE", "browser").strip().lower(),
        tts_enabled=_bool("TTS_ENABLED", True),
        piper_voices={"es": _path(os.getenv("PIPER_VOICE_ES", "voice_assistant/models/es_MX-claude-high.onnx")),
                      "en": _path(os.getenv("PIPER_VOICE_EN", "voice_assistant/models/en_US-amy-medium.onnx"))},
        tts_pitch=float(os.getenv("TTS_PITCH", "1.3")),
        places_dir=_path(os.getenv("VOICE_PLACES_DIR", "../web/src/data")),
        api_prefix=os.getenv("ASSISTANT_API_PREFIX", "/api/v1").rstrip("/"),
        max_tool_rounds=int(os.getenv("ASSISTANT_MAX_TOOL_ROUNDS", "4")),
        max_audio_mb=int(os.getenv("ASSISTANT_MAX_AUDIO_MB", "15")),
        tool_result_max_chars=int(os.getenv("ASSISTANT_TOOL_RESULT_MAX_CHARS", "2400")),
    )


settings = load_settings()
