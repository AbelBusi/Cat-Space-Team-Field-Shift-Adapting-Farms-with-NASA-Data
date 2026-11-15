from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .common import ModelWarning, Open, Reliability, Strict, Location


# ---------- climate simulation ----------

class Scenario(Strict):  # ScenarioConfiguration
    rain_factor: float = Field(1.0, ge=0, le=3, description="Rain × factor in the chosen months")
    t2m_delta: float = Field(0.0, ge=-5, le=5, description="Temperature + delta (°C); evaporation is not recomputed")
    rh_delta: float = Field(0.0, ge=-30, le=30, description="Relative humidity + delta (points, kept in 0-100)")
    months: list[int] | None = Field(None, description="Lead months (1 = first projected month) the three changes "
                                     "apply to; all if null")
    dry_months: list[int] = Field(default_factory=list, description="Lead months with no rain and the driest surface "
                                  "soil of 1998-2017. Dries the soil on average, but its pre-registered check failed: read it with care")
    pet_factor: float = Field(1.0, ge=0, le=3, description="Potential evaporation × factor (experimental)")
    ws_delta: float = Field(0.0, ge=-5, le=5, description="Wind + delta, m/s (experimental)")
    allsky_delta: float = Field(0.0, ge=-10, le=10, description="Sunlight + delta, MJ/m²/day (experimental)")
    analog: Literal["all", "el_nino"] | list[int] = Field("all", description="Weather years used: all, only coastal "
                                                         "El Niño years, or an explicit list")


class SimulationRequest(Strict):
    location: Location
    start: str = Field("2025-12", pattern=r"^\d{4}-\d{2}$", description="Last observed month (YYYY-MM)")
    horizon: int = Field(6, ge=1, le=12, description="Months to project")
    scenario: Scenario = Field(default_factory=Scenario)
    include_ndvi: bool = Field(True, description="Add the quarterly NDVI (only when start is the end of a quarter)")

    @model_validator(mode="after")
    def months_in_horizon(self):
        for name in ("months", "dry_months"):
            v = getattr(self.scenario, name) or []
            if any(k < 1 or k > self.horizon for k in v):
                raise ValueError(f"scenario.{name} must be between 1 and horizon ({self.horizon})")
        return self


class Series(BaseModel):
    median: list[float | None]
    low_90: list[float | None]
    high_90: list[float | None]
    members: int
    analog_years: list[int]


class PeriodComparison(BaseModel):
    period: str
    lead: int
    absolute_difference: float | None
    percentage_change: float | None
    direction: Literal["increased", "decreased", "unchanged"] | None
    within_model_error: bool | None = Field(description="|difference| smaller than the model's validation RMSE: "
                                            "indistinguishable from model noise")
    within_useful_lead: bool


class SimulationResponse(Open):
    location: dict
    start: str
    model: dict
    target: dict
    periods: list[str]
    baseline: Series
    scenario: Series
    comparison: list[PeriodComparison]
    modified_inputs: list[str]
    out_of_training_range: dict[str, float]
    reliability: dict
    interpretation: dict
    simulation_id: str | None = None
    reliability_level: Reliability | None = None
    warnings: list[ModelWarning] = []
    ndvi: dict | None = None




ScenarioConfiguration = Scenario
Start = Field("2025-12", pattern=r"^\d{4}-\d{2}$", description="Last observed month (YYYY-MM)")


class DroughtRequest(Strict):
    location: Location
    start: str = Start
    months: int = Field(2, ge=1, le=6, description="Months without rain in a row")
    from_lead: int = Field(1, ge=1, le=12, description="First dry month (1 = the month after start)")
    rain_factor_other: float = Field(1.0, ge=0, le=3, description="Rain × factor in the other months")
    t2m_delta: float = Field(0.0, ge=-5, le=5)
    analog: Literal["all", "el_nino"] | list[int] = "all"
    horizon: int = Field(6, ge=1, le=12)

    @model_validator(mode="after")
    def fits(self):
        if self.from_lead + self.months - 1 > self.horizon:
            raise ValueError("the drought must end within the horizon")
        return self


class ElNinoRequest(Strict):
    location: Location
    start: str = Start
    horizon: int = Field(6, ge=1, le=12)
    t2m_delta: float = Field(0.0, ge=-5, le=5)
    dry_months: list[int] = []


class TemperatureRequest(Strict):
    location: Location
    start: str = Start
    horizon: int = Field(6, ge=1, le=12)
    delta: Literal[-2, -1, 1, 2, 3] = 1
    months: list[int] | None = None


class RainfallRequest(Strict):
    location: Location
    start: str = Start
    horizon: int = Field(6, ge=1, le=12)
    rain_factor: float = Field(1.0, ge=0, le=3)
    dry_months: list[int] = []
    months: list[int] | None = None


class RecoveryRequest(Strict):
    location: Location
    start: str = Start
    drought_months: int = Field(3, ge=1, le=6)
    after: Literal["normal", "el_nino"] = "normal"
    horizon: int = Field(12, ge=7, le=12)
