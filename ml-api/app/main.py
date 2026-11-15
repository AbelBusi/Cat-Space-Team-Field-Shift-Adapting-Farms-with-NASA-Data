"""Field Shift ML API: serves the tested XGBoost models for the "What's ahead" simulator of the web app.

    uvicorn app.main:app --reload --port 8000        # from the ml-api folder; docs at /docs
"""
import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from . import service
from .config import settings
from .schemas import Location, PredictionRequest, PredictionResponse, SimulationRequest, SimulationResponse

logging.basicConfig(level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("ml-api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    service.load()            # once, at startup; never per request
    yield


app = FastAPI(title="Field Shift ML API", version=settings.service_version, lifespan=lifespan,
              description="Inference with the tested XGBoost models of Field Shift (root-zone soil water and NDVI, "
                          "Lambayeque 2 km grid). Predictions are model outputs with measured errors, not certainties.")
app.add_middleware(GZipMiddleware, minimum_size=2000)
app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


@app.exception_handler(service.ModelUnavailable)
async def unavailable(_: Request, e: service.ModelUnavailable):
    return JSONResponse(status_code=503, content={"error": "model_unavailable", "detail": str(e)})


@app.exception_handler(RequestValidationError)
async def invalid(_: Request, e: RequestValidationError):
    errs = [{"field": ".".join(str(x) for x in err["loc"][1:]), "message": err["msg"]} for err in e.errors()]
    return JSONResponse(status_code=422, content={"error": "invalid_input", "detail": errs})


@app.exception_handler(Exception)
async def internal(_: Request, e: Exception):
    log.exception("unhandled error")
    return JSONResponse(status_code=500, content={"error": "internal_error", "detail": "inference failed; see the server log"})


v1 = APIRouter(prefix="/api/v1")


@v1.get("/health")
def health():
    ok = service.STATE is not None
    return {"status": "ok" if ok else "degraded", "service_version": settings.service_version,
            "model_loaded": ok, "model_available": ok, "error": None if ok else service.LOAD_ERROR}


@v1.get("/model/info")
def model_info():
    return service.model_info()


@v1.get("/projections")
def projections():
    """Every Lambayeque 2 km cell, 12 months of root-zone soil water and 4 quarters of NDVI from the last observed month,
    for the scenarios that passed their checks. Integers x meta.scale. Computed once at startup by the tested models."""
    return service.projections()


@v1.get("/projections/cell")
def projection_cell(lat: float | None = None, lon: float | None = None, cell_id: str | None = None,
                    variable: str = "soil_water", scenario: str = "base"):
    try:
        return service.projection_at(Location(lat=lat, lon=lon, cell_id=cell_id), variable, scenario)
    except LookupError as e:
        return JSONResponse(status_code=400, content={"error": "unknown_location", "detail": str(e)})
    except ValueError as e:
        return JSONResponse(status_code=422, content={"error": "invalid_input", "detail": str(e)})


@v1.post("/predictions", response_model=PredictionResponse)
def predictions(req: PredictionRequest):
    problems = service.validate_features(req.model, req.features)
    if problems:
        return JSONResponse(status_code=422, content={"error": "invalid_input", "detail": problems})
    return service.predict_one(req.model, req.features)


@v1.post("/simulations/climate", response_model=SimulationResponse)
def simulate(req: SimulationRequest):
    service.state()
    try:
        return service.simulate(req)
    except LookupError as e:
        return JSONResponse(status_code=400, content={"error": "unknown_location", "detail": str(e)})
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": "bad_request", "detail": str(e)})


app.include_router(v1)
