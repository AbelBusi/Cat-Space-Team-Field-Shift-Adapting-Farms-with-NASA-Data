from fastapi import APIRouter

from ..schemas import (DroughtRequest, ElNinoRequest, RainfallRequest, RecoveryRequest, Scenario, SimulationRequest,
                       SimulationResponse, TemperatureRequest)
from ..services import scenario_engine as eng
from ..services.common import NotFound

router = APIRouter(prefix="/simulations", tags=["simulations"])
R = SimulationResponse


def _months(a: int, n: int):
    return list(range(a, a + n))


@router.post("/climate", response_model=R, summary="Any what-if for one cell against a normal year (the original simulator)")
def climate(req: SimulationRequest):
    return eng.run(req.location, req.start, req.horizon, req.scenario, "climate", req.include_ndvi, req.model_dump())


@router.post("/custom", response_model=R, summary="All weather inputs at once (experimental: changes of evaporation, wind or sunlight are not validated)")
def custom(req: SimulationRequest):
    return eng.run(req.location, req.start, req.horizon, req.scenario, "custom", req.include_ndvi, req.model_dump())


@router.post("/drought", response_model=R, summary="1-6 months without rain, optionally less rain in the other months and warmer")
def drought(req: DroughtRequest):
    dry = _months(req.from_lead, req.months)
    other = [k for k in range(1, req.horizon + 1) if k not in dry]
    partial = req.rain_factor_other != 1
    cfg = Scenario(dry_months=dry, rain_factor=req.rain_factor_other, t2m_delta=req.t2m_delta, analog=req.analog,
                   months=other if partial else None)
    res = eng.run(req.location, req.start, req.horizon, cfg, "drought", True, req.model_dump())
    if partial and req.t2m_delta:
        res = res | {"warnings": res["warnings"] + [{"code": "simplified", "affected": ["t2m_c"],
                     "message": "With a partial rain cut, the temperature change applies to the non-dry months only."}]}
    return res


@router.post("/el-nino", response_model=R, summary="Only the coastal El Niño years as weather, optionally with changes")
def el_nino(req: ElNinoRequest):
    cfg = Scenario(analog="el_nino", t2m_delta=req.t2m_delta, dry_months=req.dry_months)
    return eng.run(req.location, req.start, req.horizon, cfg, "el_nino", True, req.model_dump())


@router.post("/temperature", response_model=R, summary="Temperature ± °C: a direct sensitivity test (evaporation not recomputed)")
def temperature(req: TemperatureRequest):
    cfg = Scenario(t2m_delta=req.delta, months=req.months)
    return eng.run(req.location, req.start, req.horizon, cfg, "temperature", True, req.model_dump())


@router.post("/rainfall", response_model=R, summary="Less or more rain, or months without rain (experimental until check S3 passes)")
def rainfall(req: RainfallRequest):
    cfg = Scenario(rain_factor=req.rain_factor, dry_months=req.dry_months, months=req.months)
    return eng.run(req.location, req.start, req.horizon, cfg, "rainfall", True, req.model_dump())


@router.post("/recovery", response_model=R, summary="How soil water comes back after 1-6 dry months")
def recovery(req: RecoveryRequest):
    cfg = Scenario(dry_months=_months(1, req.drought_months), analog="el_nino" if req.after == "el_nino" else "all")
    res = eng.run(req.location, req.start, req.horizon, cfg, "recovery", True, req.model_dump())
    return res | {"recovery": eng.recovery_summary(res, req.drought_months)}


@router.get("/{simulation_id}/results", response_model=R, summary="A recent simulation by id (kept in memory)")
def results(simulation_id: str):
    hit = eng.RESULTS.get(simulation_id)
    if not hit:
        raise NotFound("unknown or expired simulation_id: run the simulation again (results are kept in memory only)")
    return hit
