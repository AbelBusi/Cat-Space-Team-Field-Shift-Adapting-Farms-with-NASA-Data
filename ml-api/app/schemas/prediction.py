from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .common import ModelName, Open, Reliability, Strict, Location


# ---------- single prediction ----------

class PredictionRequest(Strict):
    model: ModelName = Field(description="sm_root_monthly_v3 (root-zone soil water, the app's model), sm_root_monthly (v1, kept as reference) or ndvi_quarterly (greenness)")
    features: dict[str, float | None] = Field(description="Every feature of the model, by its training name. null = "
                                              "missing (only where training also had missing values)")

    @field_validator("features")
    @classmethod
    def finite(cls, v):
        bad = [k for k, x in v.items() if x is not None and not math.isfinite(x)]
        if bad:
            raise ValueError(f"not finite: {bad}")
        return v


class Interval(BaseModel):  # ConfidenceInterval
    low: float
    high: float
    nominal: float
    method: str
    tested_coverage: float | None = Field(description="Real share of 2023-2025 values that fell inside this interval")


class PredictionResponse(Open):
    model: str
    target: dict
    prediction: float
    interval_90: Interval
    out_of_training_range: list[str] = Field(description="Features outside the 1998-2017 p01-p99 range")
    far_out_of_training_range: list[str] = Field(description="Features outside the 1998-2017 min-max range")
    missing_features: list[str]
    warnings: list[str]
    prediction_id: str | None = None
    reliability: Reliability | None = None




class CellPredictionRequest(Strict):
    """Either a full feature set, or a cell and a period of the observed data cube (features built as in training)."""
    features: dict[str, float | None] | None = None
    location: Location | None = None
    period: str | None = Field(None, description="YYYY-MM (soil water) or YYYYQn (NDVI)", examples=["2024-03"])

    @model_validator(mode="after")
    def one_way(self):
        if (self.features is None) == (self.location is None):
            raise ValueError("give features, or location and period")
        if self.location is not None and not self.period:
            raise ValueError("period is required with location")
        if self.features:
            bad = [k for k, x in self.features.items() if x is not None and not math.isfinite(x)]
            if bad:
                raise ValueError(f"not finite: {bad}")
        return self


class BatchRequest(Strict):
    model: ModelName
    items: list[dict[str, float | None]] = Field(min_length=1, max_length=1000)

    @field_validator("items")
    @classmethod
    def finite(cls, v):
        for k, it in enumerate(v):
            bad = [f for f, x in it.items() if x is not None and not math.isfinite(x)]
            if bad:
                raise ValueError(f"item {k}: not finite: {bad}")
        return v


class CompleteRequest(Strict):
    location: Location
    quarter: str = Field(pattern=r"^\d{4}Q[1-4]$", examples=["2024Q1"])
