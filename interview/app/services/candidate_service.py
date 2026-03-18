"""Candidate service - add from resume, send invite email, manage status."""

import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate_profile import CandidateProfile, CandidateStatus
from app.models.interview_session import InterviewSession
from app.models.user import User, UserRole
from app.services.email_service import send_invite_email
from app.config import get_settings
from app.auth.password import hash_password as _hash_password
from app.auth.jwt import create_interview_link_token


def _generate_password() -> str:
    """Generate a random temporary password for the candidate."""
    return secrets.token_urlsafe(12)


def _next_interview_slot_utc() -> datetime:
    """Return next available interview slot in the configured window (e.g. 11:00 AM–5:00 PM) as UTC."""
    settings = get_settings()
    tz_name = getattr(settings, "interview_timezone", "UTC") or "UTC"
    start_hour = getattr(settings, "interview_window_start_hour", 11)
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = timezone.utc
    now = datetime.now(tz)
    # Next slot: today at start_hour if we're before start_hour; otherwise tomorrow at start_hour
    today_start = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    if now < today_start:
        slot_local = today_start
    else:
        slot_local = today_start + timedelta(days=1)
    return slot_local.astimezone(timezone.utc)


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
    ats_details: dict | None = None,
) -> tuple[User, CandidateProfile, str, bool, str]:
    """
    Create a candidate user and profile, optionally send invite email.
    Returns (user, profile, plain_password, email_sent, email_error).
    email_sent is True if invite was sent successfully; email_error is set when send failed.
    If interview_scheduled_at is None, defaults to 24–48 hours from now (placeholder).
    """
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise ValueError(f"Email already registered: {email}")

    # Use name from resume; if missing, fall back to part before @ so list shows something
    display_name = (full_name or "").strip() or None
    if not display_name and email and "@" in email:
        display_name = email.split("@")[0].strip() or None

    password = _generate_password()
    user = User(
        email=email,
        hashed_password=_hash_password(password),
        full_name=display_name,
        role=UserRole.CANDIDATE,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    if interview_scheduled_at is None:
        # Default: next slot in configured window (e.g. 11:00 AM–5:00 PM)
        interview_scheduled_at = _next_interview_slot_utc()

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
        ats_details=ats_details,
    )
    db.add(profile)
    await db.flush()
    await db.refresh(profile)
    await db.refresh(user)

    email_sent = False
    email_error = ""
    if send_email:
        settings = get_settings()
        interview_link_url = ""
        if getattr(settings, "interview_web_url", "").strip():
            link_token = create_interview_link_token(user.id)
            base = settings.interview_web_url.strip().rstrip("/")
            interview_link_url = f"{base}/exam?token={link_token}"
        email_sent, email_error = send_invite_email(
            to_email=email,
            password=password,
            interview_scheduled_at=interview_scheduled_at,
            setup_download_url=settings.setup_app_download_url,
            candidate_name=display_name,
            interview_link_url=interview_link_url or None,
        )

    return user, profile, password, email_sent, email_error


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
    """Get candidates with optimized query - excludes large text fields for list view."""
    from sqlalchemy.orm import load_only
    
    # Only load necessary columns for list view (exclude resume_text, ats_details which can be large)
    q = (
        select(CandidateProfile, User)
        .join(User, CandidateProfile.user_id == User.id)
        .options(
            load_only(
                CandidateProfile.id,
                CandidateProfile.user_id,
                CandidateProfile.job_role,
                CandidateProfile.tech_stack,
                CandidateProfile.links,
                CandidateProfile.projects,
                CandidateProfile.certificates,
                CandidateProfile.experience,
                CandidateProfile.source,
                CandidateProfile.status,
                CandidateProfile.ats_score,
                CandidateProfile.resume_url,
                CandidateProfile.interview_scheduled_at,
                CandidateProfile.invited_at,
                CandidateProfile.photo_url,
                CandidateProfile.created_at,
                CandidateProfile.updated_at,
            ),
            load_only(
                User.id,
                User.email,
                User.full_name,
            ),
        )
    )
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
