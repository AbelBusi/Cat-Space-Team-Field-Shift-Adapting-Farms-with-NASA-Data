from typing import Literal

from fastapi import APIRouter, Query

from ..services import alerts, analysis

router = APIRouter(tags=["analysis"])
Scen = Literal["base", "el_nino", "drought_feb_mar"]


@router.get("/analysis/districts", summary="Districts with cells, observed and projected values")
def districts(province: str | None = None):
    return analysis.districts(province)


@router.get("/analysis/water-retention", summary="Districts ranked by projected dry-season soil water")
def water_retention(scenario: Scen = "base", province: str | None = None):
    return analysis.ranking("water-retention", scenario, province)


@router.get("/analysis/vegetation", summary="Districts ranked by projected second-half NDVI")
def vegetation(scenario: Scen = "base", province: str | None = None):
    return analysis.ranking("vegetation", scenario, province)


@router.get("/analysis/drought-risk", summary="Share of analog years leading to dry soil (experimental unless S5 passed)")
def drought_risk(scenario: Scen = "base", lead: int = Query(3, ge=1, le=12), province: str | None = None):
    return analysis.drought_risk(scenario, lead, province)


@router.get("/analysis/anomalies", summary="Observed minus predicted, in units of the model error")
def anomalies(variable: Literal["soil_water", "ndvi"] = "soil_water", period: str = "2025-12", province: str | None = None):
    return analysis.anomalies(variable, period, province)


@router.get("/analysis/hotspots", summary="Patches persistently greener than the weather explains (experimental)")
def hotspots(since: str = "2024Q1", min_quarters: int = Query(3, ge=1, le=12), province: str | None = None):
    return analysis.hotspots(since, min_quarters, province)


@router.get("/alerts/drought", summary="Cells with soil water below the band expected one month earlier")
def alert_drought(month: str = Query("2025-12", pattern=r"^\d{4}-\d{2}$")):
    return alerts.drought(month)


@router.get("/alerts/vegetation", summary="Cells with NDVI below the band expected one quarter earlier")
def alert_vegetation(quarter: str = Query("2025Q4", pattern=r"^\d{4}Q[1-4]$")):
    return alerts.vegetation(quarter)
