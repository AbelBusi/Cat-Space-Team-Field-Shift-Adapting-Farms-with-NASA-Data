"""Field Shift ML API: serves the tested XGBoost models (root-zone soil water and NDVI, Lambayeque 2 km grid).

    uvicorn app.main:app --port 8000        # from the ml-api folder; docs at /docs
Expansion plan and status of every endpoint: roadmap/README.md."""
import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .config import settings
from .routers import analysis, ask, explanations, models, predictions, projections, simulations
from .services import state
from .services.common import BadRequest, ModelUnavailable, NotFound

logging.basicConfig(level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("ml-api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    state.load()            # once, at startup; never per request
    yield


app = FastAPI(title="Field Shift ML API", version=settings.service_version, lifespan=lifespan,
              description="Inference with the tested XGBoost models of Field Shift (root-zone soil water and NDVI, "
                          "Lambayeque 2 km grid): predictions, projections, simulations, territorial analysis, alerts, "
                          "explanations and monitoring. Every answer carries its reliability level and warnings; "
                          "predictions are model outputs with measured errors, not certainties.")
app.add_middleware(GZipMiddleware, minimum_size=2000)
app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


@app.exception_handler(ModelUnavailable)
async def unavailable(_: Request, e: ModelUnavailable):
    return JSONResponse(status_code=503, content={"error": "model_unavailable", "detail": str(e)})


@app.exception_handler(RequestValidationError)
async def invalid(_: Request, e: RequestValidationError):
    errs = [{"field": ".".join(str(x) for x in err["loc"][1:]), "message": err["msg"]} for err in e.errors()]
    return JSONResponse(status_code=422, content={"error": "invalid_input", "detail": errs})


@app.exception_handler(ValidationError)          # Pydantic models built inside a route (e.g. Location from query params)
async def invalid_inner(_: Request, e: ValidationError):
    return JSONResponse(status_code=422, content={"error": "invalid_input", "detail": [x["msg"] for x in e.errors()]})


@app.exception_handler(NotFound)                 # a cell, period or id that does not exist
async def not_found(_: Request, e: NotFound):
    return JSONResponse(status_code=400, content={"error": "unknown_location_or_id", "detail": str(e).strip("'\"")})


@app.exception_handler(BadRequest)               # a request that cannot be answered (start month, scenario name, …)
async def bad_request(_: Request, e: BadRequest):
    return JSONResponse(status_code=400, content={"error": "bad_request", "detail": str(e)})


@app.exception_handler(Exception)
async def internal(_: Request, e: Exception):
    log.exception("unhandled error")
    return JSONResponse(status_code=500, content={"error": "internal_error", "detail": "inference failed; see the server log"})


v1 = APIRouter(prefix="/api/v1")
for r in (models, predictions, projections, simulations, analysis, explanations, ask):
    v1.include_router(r.router)
app.include_router(v1)
