"""Candidate profile - from Naukri/resume, job role, tech stack, invite status."""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class CandidateStatus(str, PyEnum):
    """Candidate pipeline status."""

    INVITED = "invited"  # Email sent with credentials + interview time
    SCHEDULED = "scheduled"  # Interview time confirmed
    IN_PROGRESS = "in_progress"  # Currently in interview
    COMPLETED = "completed"  # Interview done, awaiting admin decision
    NEXT_ROUND = "next_round"  # Admin allowed for next round
    SELECTED = "selected"
    REJECTED = "rejected"


class CandidateProfile(Base):
    """Candidate from resume (Naukri/manual), linked to User for login."""

    __tablename__ = "candidate_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    job_role: Mapped[str] = mapped_column(String(255), nullable=False)
    tech_stack: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # e.g. ["Python", "React"]
    links: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # URLs from resume (GitHub, LinkedIn, etc.)
    projects: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # Project names/descriptions
    certificates: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # Certifications
    experience: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # Experience entries
    source: Mapped[str] = mapped_column(String(64), default="manual", nullable=False)  # naukri, manual, csv, platform
    ats_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # ATS score from platform; shortlist if >= 85
    ats_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # { matched_skills, missing_skills, suggestions }
    resume_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    resume_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    interview_scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=CandidateStatus.INVITED.value, nullable=False)
    invited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)  # Captured at interview start
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    user: Mapped["User"] = relationship("User", backref="candidate_profile", foreign_keys=[user_id])
