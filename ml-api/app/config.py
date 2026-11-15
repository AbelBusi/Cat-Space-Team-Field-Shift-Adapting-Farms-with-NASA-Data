"""Settings from environment variables (see .env.example). Paths are relative to the ml-api folder."""
import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
    # Monthly inputs 1998-2025 per Lambayeque cell, written by ml/scripts/export_api_cube.py
    cube_path: Path = field(default_factory=lambda: _path("FS_CUBE_PATH", "data/cube.npz"))
    cors_origins: tuple = field(default_factory=lambda: tuple(o.strip() for o in os.environ.get(
        "ML_API_CORS_ORIGINS", "http://localhost:5173,http://localhost:5174").split(",") if o.strip()))
    log_level: str = field(default_factory=lambda: os.environ.get("ML_API_LOG_LEVEL", "info"))


settings = Settings()
