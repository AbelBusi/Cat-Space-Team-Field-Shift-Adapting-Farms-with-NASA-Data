from typing import Literal

from fastapi import APIRouter

from ..schemas import Location
from ..services import projections

router = APIRouter(prefix="/projections", tags=["projections"])


@router.get("", summary="Every Lambayeque cell: 12 months of soil water and 4 quarters of NDVI per scenario (integers x 1000)")
def bundle():
    return projections.projections()


@router.get("/cell", summary="One cell's projection in real units")
def cell(lat: float | None = None, lon: float | None = None, cell_id: str | None = None,
         variable: Literal["soil_water", "ndvi"] = "soil_water", scenario: str = "base"):
    return projections.projection_at(Location(lat=lat, lon=lon, cell_id=cell_id), variable, scenario)
