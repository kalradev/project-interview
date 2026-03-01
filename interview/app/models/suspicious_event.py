"""Suspicious event model - timestamped events (tab switch, paste, etc.)."""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.interview_session import InterviewSession


class EventType(str, PyEnum):
    """Types of suspicious events."""

    TAB_SWITCH = "tab_switch"
    PASTE = "paste_event"
    COPY = "copy_event"
    DEVTOOLS = "devtools_detection"
    IDLE = "idle_time"
    BURST_TYPING = "burst_typing"
    INSTANT_LARGE_INPUT = "instant_large_input"
    WEBCAM_ANOMALY = "webcam_anomaly"


class SuspiciousEvent(Base):
    """Timestamped suspicious event during an interview session."""

    __tablename__ = "suspicious_events"

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
    event_type: Mapped[EventType] = mapped_column(Enum(EventType), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    severity: Mapped[str] = mapped_column(String(16), default="medium", nullable=True)

    session: Mapped["InterviewSession"] = relationship(
        "InterviewSession",
        back_populates="suspicious_events",
    )
