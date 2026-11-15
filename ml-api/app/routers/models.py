from fastapi import APIRouter

from ..config import settings
from ..services import monitoring

router = APIRouter(tags=["models"])


@router.get("/health", summary="API and model status")
@router.get("/models/health", summary="API and model status (alias)")
def health():
    return monitoring.health() | {"service_version": settings.service_version}


@router.get("/model/info", summary="Everything known about the two models")
def model_info():
    return monitoring.info()


@router.get("/models/metrics", summary="Historical metrics per period (not the precision of one prediction)")
def metrics():
    return monitoring.metrics()


@router.get("/models/validation", summary="Acceptance criteria, projection skill and Phase 2 checks")
def validation():
    return monitoring.validation()
