"""User model for authentication and role-based access."""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, String, TypeDecorator
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class UserRole(str, PyEnum):
    """User roles for RBAC."""

    ADMIN = "admin"
    INTERVIEWER = "interviewer"
    CANDIDATE = "candidate"


# PostgreSQL enum 'userrole' - if you see "invalid input value for enum userrole: 'candidate'",
# the DB likely has uppercase labels; use name="userrole", values uppercase, create_type=False.
USERROLE_ENUM = ENUM(
    "ADMIN",
    "INTERVIEWER",
    "CANDIDATE",
    name="userrole",
    create_type=False,
)

# Map DB values (any casing) to UserRole for reading
_ROLE_MAP = {v.value: v for v in UserRole} | {v.name: v for v in UserRole} | {v.value.upper(): v for v in UserRole}


class _UserRoleType(TypeDecorator):
    """Binds UserRole as enum name (e.g. CANDIDATE) for DB; reads back any casing as UserRole."""
    impl = USERROLE_ENUM
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, UserRole):
            return value.value  # Use lowercase value ('admin') to match DB enum
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, UserRole):
            return value
        raw = (value.strip() if isinstance(value, str) else str(value).strip()).upper()
        return _ROLE_MAP.get(raw) or _ROLE_MAP.get(value.strip().lower() if isinstance(value, str) else "") or UserRole.CANDIDATE


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
        _UserRoleType(),
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
