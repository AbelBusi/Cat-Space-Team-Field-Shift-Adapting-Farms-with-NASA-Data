from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ModelName = Literal["sm_root_monthly", "sm_root_monthly_v3", "ndvi_quarterly"]
Reliability = Literal["ok", "warning", "out_of_domain", "experimental"]


class Strict(BaseModel):
    """Requests reject unknown fields (422), so a typo never silently becomes "missing"."""
    model_config = ConfigDict(extra="forbid")


class Open(BaseModel):
    """Responses keep every field the service returns (new fields are never dropped silently)."""
    model_config = ConfigDict(extra="allow")


class ModelWarning(BaseModel):
    code: str = Field(description="out_of_range, out_of_domain, beyond_useful_lead, rain_only, few_analogs, "
                                  "pet_not_recomputed, experimental, within_model_error, inconsistent, in_training, not_harvest")
    message: str
    affected: list[str] = []


class Location(Strict):
    """A 2 km cell of the Lambayeque grid: by id, or by a point inside it."""
    cell_id: str | None = Field(None, description="Grid cell 'x,y' (2 km)", examples=["-4410,-357"])
    lat: float | None = Field(None, ge=-90, le=90)
    lon: float | None = Field(None, ge=-180, le=180)

    @model_validator(mode="after")
    def one_way(self):
        if self.cell_id is None and (self.lat is None or self.lon is None):
            raise ValueError("give cell_id, or lat and lon")
        return self


