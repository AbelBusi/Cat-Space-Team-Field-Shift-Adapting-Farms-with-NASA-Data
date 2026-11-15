from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..schemas import PredictionRequest
from ..services import explanations, prediction

router = APIRouter(prefix="/explanations", tags=["explanations"])


@router.get("/{prediction_id}", summary="TreeSHAP contributions of a recent prediction")
def by_id(prediction_id: str):
    return explanations.by_id(prediction_id)


@router.post("", summary="TreeSHAP contributions for a full feature set")
def explain(req: PredictionRequest):
    problems = prediction.validate_features(req.model, req.features)
    if problems:
        return JSONResponse(status_code=422, content={"error": "invalid_input", "detail": problems})
    return explanations.explain(req.model, req.features)
