"""Integrity score Pydantic schemas."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class RiskLevel(str):
    """Risk level string literal."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class IntegrityScoreResponse(BaseModel):
    """Schema for integrity score response."""

    id: UUID
    session_id: UUID
    score: float
    risk_level: str
    penalties: Optional[dict[str, Any]] = None
    computed_at: datetime

    model_config = {"from_attributes": True}
