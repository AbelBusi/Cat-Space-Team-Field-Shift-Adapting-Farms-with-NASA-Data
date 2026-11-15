from fastapi import APIRouter
from fastapi.responses import JSONResponse

from .. import ask as sprout
from ..config import settings
from ..schemas import AskRequest, AskResponse

router = APIRouter(tags=["sprout"])


@router.post("/ask", response_model=AskResponse, summary="Sprout answers with its persona and the numbers on screen")
def ask(req: AskRequest):
    try:
        return {"answer": sprout.answer(req.question, req.lang, req.context, req.history), "model": settings.llm_model}
    except sprout.AskUnavailable as e:
        return JSONResponse(status_code=503, content={"error": "ai_unavailable", "detail": str(e)})
