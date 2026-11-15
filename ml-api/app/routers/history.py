from fastapi import APIRouter

from ..services import history as svc

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", summary="The whole department since 1998: monthly soil water of every Lambayeque square and the facts of the History mode")
def department_history():
    return svc.history()
