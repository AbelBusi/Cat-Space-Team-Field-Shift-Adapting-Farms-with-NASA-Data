"""Request and response bodies. Extra fields are rejected (422) so a typo never silently becomes "missing"."""
from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ModelName = Literal["sm_root_monthly", "ndvi_quarterly"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------- single prediction ----------

class PredictionRequest(Strict):
    model: ModelName = Field(description="sm_root_monthly (root-zone soil water) or ndvi_quarterly (greenness)")
    features: dict[str, float | None] = Field(description="Every feature of the model, by its training name. null = "
                                              "missing (only where training also had missing values)")

    @field_validator("features")
    @classmethod
    def finite(cls, v):
        bad = [k for k, x in v.items() if x is not None and not math.isfinite(x)]
        if bad:
            raise ValueError(f"not finite: {bad}")
        return v


class Interval(BaseModel):
    low: float
    high: float
    nominal: float
    method: str
    tested_coverage: float | None = Field(description="Real share of 2023-2025 values that fell inside this interval")


class PredictionResponse(BaseModel):
    model: str
    target: dict
    prediction: float
    interval_90: Interval
    out_of_training_range: list[str] = Field(description="Features outside the 1998-2017 p01-p99 range")
    far_out_of_training_range: list[str] = Field(description="Features outside the 1998-2017 min-max range")
    missing_features: list[str]
    warnings: list[str]


# ---------- climate simulation ----------

class Location(Strict):
    cell_id: str | None = Field(None, description="Grid cell 'x,y' (2 km)", examples=["-4410,-357"])
    lat: float | None = Field(None, ge=-90, le=90)
    lon: float | None = Field(None, ge=-180, le=180)

    @model_validator(mode="after")
    def one_way(self):
        if self.cell_id is None and (self.lat is None or self.lon is None):
            raise ValueError("give cell_id, or lat and lon")
        return self


class Scenario(Strict):
    rain_factor: float = Field(1.0, ge=0, le=3, description="Rain × factor in the chosen months")
    t2m_delta: float = Field(0.0, ge=-5, le=5, description="Temperature + delta (°C); evaporation is not recomputed")
    rh_delta: float = Field(0.0, ge=-30, le=30, description="Relative humidity + delta (points, kept in 0-100)")
    months: list[int] | None = Field(None, description="Lead months (1 = first projected month) the three changes "
                                     "apply to; all if null")
    dry_months: list[int] = Field(default_factory=list, description="Lead months with no rain and the driest surface "
                                  "soil of 1998-2017 (the drought case that passed its check)")
    analog: Literal["all", "el_nino"] | list[int] = Field("all", description="Weather years used: all, only coastal "
                                                         "El Niño years, or an explicit list")


class SimulationRequest(Strict):
    location: Location
    start: str = Field("2025-12", pattern=r"^\d{4}-\d{2}$", description="Last observed month (YYYY-MM)")
    horizon: int = Field(6, ge=1, le=12, description="Months to project")
    scenario: Scenario = Field(default_factory=Scenario)

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


class SimulationResponse(BaseModel):
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


# ---------- Sprout's open questions ----------

class ChatTurn(Strict):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=2000)


class AskRequest(Strict):
    question: str = Field(min_length=1, max_length=600)
    lang: Literal["en", "es", "qu"] = "en"
    context: dict = Field(default_factory=dict, description="What the user sees: place, lat/lon, month, readings, topic")
    history: list[ChatTurn] = Field(default_factory=list, max_length=12, description="Earlier turns of this conversation")


class AskResponse(BaseModel):
    answer: str
    model: str
