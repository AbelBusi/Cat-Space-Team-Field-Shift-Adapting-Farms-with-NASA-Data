from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .common import Strict


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
