from fastapi import APIRouter

from ..schemas import Location
from ..services import timeline as svc

router = APIRouter(prefix="/timeline", tags=["timeline"])


@router.get("", summary="One cell through time: observed soil water (3 layers), rain and NDVI since 1998, the model's months and the projection")
def cell_timeline(lat: float | None = None, lon: float | None = None, cell_id: str | None = None):
    return svc.timeline(Location(lat=lat, lon=lon, cell_id=cell_id))
