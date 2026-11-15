from typing import Literal

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from ..schemas import BatchRequest, CellPredictionRequest, CompleteRequest, PredictionRequest, PredictionResponse
from ..services import prediction as svc

router = APIRouter(prefix="/predictions", tags=["predictions"])


def _invalid(problems):
    return JSONResponse(status_code=422, content={"error": "invalid_input", "detail": problems})


@router.post("", response_model=PredictionResponse, summary="One prediction from a full feature set (either model)")
def predict(req: PredictionRequest):
    problems = svc.validate_features(req.model, req.features)
    return _invalid(problems) if problems else svc.predict_one(req.model, req.features)


def _one(variable: str, req: CellPredictionRequest):
    if req.features is not None:
        name = svc.model_for(variable, req.features)
        problems = svc.validate_features(name, req.features)
        return _invalid(problems) if problems else svc.predict_one(name, req.features)
    return svc.predict_cell(variable, req.location, req.period)


@router.post("/soil-water", response_model=PredictionResponse, summary="Monthly root-zone soil water (features, or cell + month)")
def soil_water(req: CellPredictionRequest):
    return _one("soil_water", req)


@router.post("/ndvi", response_model=PredictionResponse, summary="Quarterly NDVI (features, or cell + quarter)")
def ndvi(req: CellPredictionRequest):
    return _one("ndvi", req)


@router.post("/complete", summary="The 3 months of soil water of a quarter and its NDVI, chained")
def complete(req: CompleteRequest):
    return svc.predict_complete(req.location, req.quarter)


@router.post("/batch", summary="Up to 1,000 predictions in one call")
def batch(req: BatchRequest):
    return svc.batch(req.model, req.items)


@router.get("/{cell_id}/history", summary="Observed values and one-step predictions of a cell, 1998-2025")
def history(cell_id: str, variable: Literal["soil_water", "ndvi"] = "soil_water",
            start: str | None = Query(None, alias="from"), end: str | None = Query(None, alias="to")):
    return svc.history(variable, cell_id, start, end)


@router.get("/{cell_id}/confidence", summary="Historical error of the model at this place (experimental unless check S10 passed)")
def confidence(cell_id: str):
    return svc.confidence(cell_id)
