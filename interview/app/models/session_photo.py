"""Session photo - captured during interview for identity verification."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class SessionPhoto(Base):
    """Photo captured during an interview session (for company to match later)."""

    __tablename__ = "session_photos"

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
    photo_url: Mapped[str] = mapped_column(String(512), nullable=False)
    face_detected: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # For lip/cheating check
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    session: Mapped["InterviewSession"] = relationship(  # noqa: F821
        "InterviewSession",
        back_populates="session_photos",
    )
