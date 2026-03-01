"""Event-related Pydantic schemas."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.suspicious_event import EventType


class EventLogRequest(BaseModel):
    """Schema for logging a suspicious event."""

    session_id: UUID
    event_type: EventType
    payload: Optional[dict[str, Any]] = None
    severity: Optional[str] = "medium"


class EventLogResponse(BaseModel):
    """Schema for logged event response."""

    id: UUID
    session_id: UUID
    event_type: EventType
    occurred_at: datetime
    severity: Optional[str] = None

    model_config = {"from_attributes": True}


class TypingEventRequest(BaseModel):
    """Schema for typing/keystroke events."""

    session_id: UUID
    keystroke_timestamps: list[float]
    text_length: int
    question_id: Optional[str] = None


class AnalyzeAnswerRequest(BaseModel):
    """Schema for answer analysis (AI + typing)."""

    session_id: UUID
    answer_text: str = ""
    question_id: Optional[str] = None
    keystroke_timestamps: Optional[list[float]] = None
