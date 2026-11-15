from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ScreenContext(BaseModel):
    """Lo que el usuario ve en pantalla (celda tocada, mes, tema...)."""
    model_config = ConfigDict(extra="forbid")

    lat: float | None = Field(None, ge=-90, le=90)
    lon: float | None = Field(None, ge=-180, le=180)
    cell_id: str | None = Field(None, max_length=40)
    district: str | None = Field(None, max_length=80)
    month: str | None = Field(None, max_length=10)
    topic: str | None = Field(None, max_length=60)
    readings: dict[str, Any] | None = None


class HistoryTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(max_length=2000)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=1000)
    context: ScreenContext | None = None
    history: list[HistoryTurn] = Field(default_factory=list, max_length=10)
    speak: bool = False


class AssistantAction(BaseModel):
    """Acción estructurada para el mapa/dashboard. 'type' + parámetros propios de cada tipo."""
    model_config = ConfigDict(extra="allow")

    type: Literal["select_cell", "run_simulation", "compare_cells", "show_analysis", "show_alerts"]


class ChatResponse(BaseModel):
    text: str
    mood: str = "neutral"
    actions: list[AssistantAction] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    audio_base64: str | None = None
    audio_mime: str | None = None
    speak_error: str | None = None


class VoiceResponse(ChatResponse):
    transcript: str


class StatusResponse(BaseModel):
    ok: bool
    assistant_name: str
    llm: dict[str, Any]
    stt: dict[str, Any]
    tts: dict[str, Any]
    tools: list[str]