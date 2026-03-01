"""Session-related Pydantic schemas."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class SessionCreate(BaseModel):
    """Schema for starting an interview session."""

    candidate_id: Optional[UUID] = None
    interviewer_id: Optional[UUID] = None
    metadata: Optional[dict[str, Any]] = None


class SessionResponse(BaseModel):
    """Schema for session in responses."""

    id: UUID
    session_token: str
    candidate_id: Optional[UUID] = None
    interviewer_id: Optional[UUID] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    status: str
    metadata: Optional[dict[str, Any]] = None

    model_config = {"from_attributes": True}


class SessionEnd(BaseModel):
    """Schema for ending a session."""

    session_id: UUID


class SessionSummaryUpdate(BaseModel):
    """Update interview summary (when interview is done)."""

    summary: str
