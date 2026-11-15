"""Settings from environment variables (see .env.example). Paths are relative to the ml-api folder."""
import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# ml-api/.env (git-ignored) fills variables that are not already set: keys stay on the server, never in git.
_env = ROOT / ".env"
if _env.exists():
    for _line in _env.read_text(encoding="utf-8").splitlines():
        _k, _, _v = _line.partition("=")
        if _k.strip() and not _k.lstrip().startswith("#") and _v.strip():
            os.environ.setdefault(_k.strip(), _v.strip())


def _path(name: str, default: str) -> Path:
    p = Path(os.environ.get(name, default))
    return p if p.is_absolute() else (ROOT / p).resolve()


@dataclass(frozen=True)
class Settings:
    service_version: str = "0.1.0"
    # The tested models, never copied or changed: ml/artifacts/final_model
    model_dir: Path = field(default_factory=lambda: _path("FS_MODEL_DIR", "../ml/artifacts/final_model"))
    # The fs_ml package (same feature code as training): its parent folder, ml/
    ml_package_dir: Path = field(default_factory=lambda: _path("FS_ML_PACKAGE_DIR", "../ml"))
    # Hindcast results of the projection layer (useful lead, range corrections): ml/artifacts/projections
    projection_card: Path = field(default_factory=lambda: _path("FS_PROJECTION_CARD", "../ml/artifacts/projections/projection_card.json"))
    # Results of the Phase 2 checks (docs/ML_API_VALIDATION.md): which new features may leave the "experimental" label
    api_checks: Path = field(default_factory=lambda: _path("FS_API_CHECKS", "../ml/artifacts/api_validation/checks.json"))
    # Monthly inputs 1998-2025 per Lambayeque cell, written by ml/scripts/export_api_cube.py
    cube_path: Path = field(default_factory=lambda: _path("FS_CUBE_PATH", "data/cube.npz"))
    cors_origins: tuple = field(default_factory=lambda: tuple(o.strip() for o in os.environ.get(
        "ML_API_CORS_ORIGINS", "http://localhost:5173,http://localhost:5174").split(",") if o.strip()))
    log_level: str = field(default_factory=lambda: os.environ.get("ML_API_LOG_LEVEL", "info"))
    # Sprout's open questions (POST /ask): any OpenAI-compatible chat endpoint. Default: Ollama on this machine.
    persona_path: Path = field(default_factory=lambda: _path("FS_PERSONA_PATH", "../docs/SPROUT_PERSONA.md"))
    llm_base_url: str = field(default_factory=lambda: os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1"))
    llm_model: str = field(default_factory=lambda: os.environ.get("LLM_MODEL", "qwen2.5:3b"))
    llm_api_key: str = field(default_factory=lambda: os.environ.get("LLM_API_KEY", ""))
    # Only for reasoning models that accept it (e.g. openai/gpt-oss on Groq): low keeps answers fast
    llm_reasoning_effort: str = field(default_factory=lambda: os.environ.get("LLM_REASONING_EFFORT", ""))
    llm_timeout: float = field(default_factory=lambda: float(os.environ.get("LLM_TIMEOUT", "60")))


settings = Settings()
