"""Answer analysis model - typing and AI detection per answer."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.interview_session import InterviewSession


class AnswerAnalysis(Base):
    """Analysis of a single answer: typing metrics and AI probability."""

    __tablename__ = "answer_analyses"

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
    question_id: Mapped[str] = mapped_column(String(64), nullable=True)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    words_per_second: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    features: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    session: Mapped["InterviewSession"] = relationship(
        "InterviewSession",
        back_populates="answer_analyses",
    )
