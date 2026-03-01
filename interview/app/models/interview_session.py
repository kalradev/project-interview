"""Interview session model - session metadata and lifecycle."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.suspicious_event import SuspiciousEvent
    from app.models.answer_analysis import AnswerAnalysis
    from app.models.integrity_score import IntegrityScore
    from app.models.session_photo import SessionPhoto


class InterviewSession(Base):
    """Interview session with unique ID and metadata."""

    __tablename__ = "interview_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_token: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    interviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    interview_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(512), nullable=True)  # Recorded interview video
    # Agent report (accuracy, communication, summary); set when session ends
    agent_report: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Face/lip check for cheating: pass | review | pending
    face_lip_status: Mapped[str | None] = mapped_column(String(32), nullable=True)

    candidate: Mapped["User | None"] = relationship(
        "User",
        back_populates="sessions_as_candidate",
        foreign_keys=[candidate_id],
    )
    interviewer: Mapped["User | None"] = relationship(
        "User",
        back_populates="sessions_as_interviewer",
        foreign_keys=[interviewer_id],
    )
    suspicious_events: Mapped[list["SuspiciousEvent"]] = relationship(
        "SuspiciousEvent",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    answer_analyses: Mapped[list["AnswerAnalysis"]] = relationship(
        "AnswerAnalysis",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    integrity_scores: Mapped[list["IntegrityScore"]] = relationship(
        "IntegrityScore",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    interview_exchanges: Mapped[list["InterviewExchange"]] = relationship(
        "InterviewExchange",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    session_photos: Mapped[list["SessionPhoto"]] = relationship(
        "SessionPhoto",
        back_populates="session",
        cascade="all, delete-orphan",
    )
