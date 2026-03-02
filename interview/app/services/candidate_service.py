"""Candidate service - add from resume, send invite email, manage status."""

import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate_profile import CandidateProfile, CandidateStatus
from app.models.interview_session import InterviewSession
from app.models.user import User
from app.models.user import User, UserRole
from app.services.email_service import send_invite_email
from app.config import get_settings
from app.auth.password import hash_password as _hash_password


def _generate_password() -> str:
    """Generate a random temporary password for the candidate."""
    return secrets.token_urlsafe(12)


async def add_candidate(
    db: AsyncSession,
    email: str,
    full_name: str,
    job_role: str,
    tech_stack: list[str] | None = None,
    resume_text: str | None = None,
    resume_url: str | None = None,
    links: list[str] | None = None,
    projects: list[str] | None = None,
    certificates: list[str] | None = None,
    experience: list[str] | None = None,
    source: str = "manual",
    interview_scheduled_at: datetime | None = None,
    send_email: bool = True,
    ats_score: float | None = None,
) -> tuple[User, CandidateProfile, str, bool]:
    """
    Create a candidate user and profile, optionally send invite email.
    Returns (user, profile, plain_password, email_sent).
    email_sent is True if invite was sent successfully, False if send_email was False or send failed.
    If interview_scheduled_at is None, defaults to 24–48 hours from now (placeholder).
    """
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise ValueError(f"Email already registered: {email}")

    password = _generate_password()
    user = User(
        email=email,
        hashed_password=_hash_password(password),
        full_name=full_name or None,
        role=UserRole.CANDIDATE,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    if interview_scheduled_at is None:
        # Default: tomorrow same time or 24h from now
        interview_scheduled_at = datetime.now(timezone.utc) + timedelta(days=1)

    profile = CandidateProfile(
        user_id=user.id,
        job_role=job_role,
        tech_stack=tech_stack or [],
        links=links,
        projects=projects,
        certificates=certificates,
        experience=experience,
        source=source,
        resume_text=resume_text,
        resume_url=resume_url,
        interview_scheduled_at=interview_scheduled_at,
        status=CandidateStatus.INVITED.value,
        invited_at=datetime.now(timezone.utc),
        ats_score=ats_score,
    )
    db.add(profile)
    await db.flush()
    await db.refresh(profile)
    await db.refresh(user)

    email_sent = False
    if send_email:
        settings = get_settings()
        email_sent = send_invite_email(
            to_email=email,
            password=password,
            interview_scheduled_at=interview_scheduled_at,
            setup_download_url=settings.setup_app_download_url,
            candidate_name=full_name,
        )

    return user, profile, password, email_sent


async def get_candidate_by_user_id(db: AsyncSession, user_id: UUID) -> Optional[CandidateProfile]:
    result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_candidates(
    db: AsyncSession,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[tuple[CandidateProfile, User]]:
    q = select(CandidateProfile, User).join(User, CandidateProfile.user_id == User.id)
    if status:
        q = q.where(CandidateProfile.status == status)
    q = q.order_by(CandidateProfile.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    return list(result.all())


async def update_candidate_status(
    db: AsyncSession,
    candidate_id: UUID,
    status: str,
) -> Optional[CandidateProfile]:
    result = await db.execute(select(CandidateProfile).where(CandidateProfile.id == candidate_id))
    profile = result.scalar_one_or_none()
    if not profile:
        return None
    profile.status = status
    await db.flush()
    await db.refresh(profile)
    return profile


async def delete_candidate(db: AsyncSession, candidate_id: UUID) -> bool:
    """
    Delete a candidate: remove their sessions, profile, and user.
    Returns True if deleted, False if candidate not found.
    """
    result = await db.execute(select(CandidateProfile).where(CandidateProfile.id == candidate_id))
    profile = result.scalar_one_or_none()
    if not profile:
        return False
    user_id = profile.user_id
    await db.execute(delete(InterviewSession).where(InterviewSession.candidate_id == user_id))
    await db.delete(profile)
    user = await db.get(User, user_id)
    if user:
        await db.delete(user)
    await db.flush()
    return True
