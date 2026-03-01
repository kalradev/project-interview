"""Integrity score model - session-level score and risk classification."""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.interview_session import InterviewSession


class RiskLevel(str, PyEnum):
    """Risk classification based on integrity score."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class IntegrityScore(Base):
    """Integrity score snapshot for an interview session."""

    __tablename__ = "integrity_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(
        String(16),
        default=RiskLevel.LOW.value,
        nullable=False,
    )
    penalties: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    session: Mapped["InterviewSession"] = relationship(
        "InterviewSession",
        back_populates="integrity_scores",
    )
