"""User model for authentication and role-based access."""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class UserRole(str, PyEnum):
    """User roles for RBAC."""

    ADMIN = "admin"
    INTERVIEWER = "interviewer"
    CANDIDATE = "candidate"


class User(Base):
    """User account for JWT auth and role-based access."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        default=UserRole.CANDIDATE,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    sessions_as_candidate = relationship(
        "InterviewSession",
        back_populates="candidate",
        foreign_keys="InterviewSession.candidate_id",
    )
    sessions_as_interviewer = relationship(
        "InterviewSession",
        back_populates="interviewer",
        foreign_keys="InterviewSession.interviewer_id",
    )
