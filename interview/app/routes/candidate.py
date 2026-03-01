"""Candidate routes - me (profile + session), get-or-create session, photo upload, session photo/video."""

import uuid as uuid_lib
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, status, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.auth.dependencies import require_roles
from app.database import get_async_session
from app.models.candidate_profile import CandidateProfile
from app.models.interview_session import InterviewSession
from app.models.session_photo import SessionPhoto
from app.models.user import User, UserRole
from app.services.session_service import SessionService

router = APIRouter()
session_service = SessionService()


@router.get("/me")
async def get_my_profile(
    db: AsyncSession = Depends(get_async_session),
    current_user=Depends(require_roles(UserRole.CANDIDATE)),
):
    """Get current candidate profile and active session (for desktop app after login)."""
    user_id = current_user["sub"]
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    profile_result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user_id)
    )
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found. You may not have been invited yet.",
        )

    session_result = await db.execute(
        select(InterviewSession)
        .where(InterviewSession.candidate_id == user_id)
        .where(InterviewSession.status == "active")
        .order_by(InterviewSession.started_at.desc())
        .limit(1)
    )
    session = session_result.scalar_one_or_none()

    return {
        "email": user.email,
        "full_name": user.full_name,
        "job_role": profile.job_role,
        "tech_stack": profile.tech_stack,
        "interview_scheduled_at": profile.interview_scheduled_at.isoformat() if profile.interview_scheduled_at else None,
        "status": profile.status,
        "session": {
            "id": str(session.id),
            "session_token": session.session_token,
        } if session else None,
    }


@router.post("/me/session")
async def get_or_create_my_session(
    db: AsyncSession = Depends(get_async_session),
    current_user=Depends(require_roles(UserRole.CANDIDATE)),
):
    """Get existing active session or create one for this candidate (so they can start the interview)."""
    user_id = current_user["sub"]
    profile_result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user_id)
    )
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found.",
        )

    existing = await db.execute(
        select(InterviewSession)
        .where(InterviewSession.candidate_id == user_id)
        .where(InterviewSession.status == "active")
        .order_by(InterviewSession.started_at.desc())
        .limit(1)
    )
    session = existing.scalar_one_or_none()
    if session:
        return {
            "session_id": str(session.id),
            "session_token": session.session_token,
            "job_role": profile.job_role,
            "tech_stack": profile.tech_stack,
        }

    from app.schemas.session import SessionCreate
    new_session = await session_service.start_session(
        db,
        SessionCreate(
            candidate_id=UUID(user_id),
            metadata={"job_role": profile.job_role, "tech_stack": profile.tech_stack or []},
        ),
    )
    return {
        "session_id": str(new_session.id),
        "session_token": new_session.session_token,
        "job_role": profile.job_role,
        "tech_stack": profile.tech_stack,
    }


@router.post("/me/photo")
async def upload_my_photo(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_session),
    current_user=Depends(require_roles(UserRole.CANDIDATE)),
):
    """Upload candidate photo (captured at interview start). Stored and linked to profile."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be an image")
    settings = get_settings()
    upload_dir = Path(settings.upload_photos_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "img").suffix or ".jpg"
    name = f"{current_user['sub']}_{uuid_lib.uuid4().hex[:8]}{ext}"
    path = upload_dir / name
    content = await file.read()
    path.write_bytes(content)
    photo_url = f"/{settings.upload_photos_dir}/{name}"

    profile_result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == UUID(current_user["sub"]))
    )
    profile = profile_result.scalar_one_or_none()
    if profile:
        profile.photo_url = photo_url
        await db.flush()

    return {"photo_url": photo_url}


@router.post("/me/session/photo")
async def upload_session_photo(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_session),
    current_user=Depends(require_roles(UserRole.CANDIDATE)),
):
    """Upload a photo captured during the interview (for company to match user later)."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be an image")
    user_id = UUID(current_user["sub"])
    session_result = await db.execute(
        select(InterviewSession)
        .where(InterviewSession.candidate_id == user_id)
        .where(InterviewSession.status == "active")
        .order_by(InterviewSession.started_at.desc())
        .limit(1)
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active session")

    settings = get_settings()
    upload_dir = Path(settings.upload_photos_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "img").suffix or ".jpg"
    name = f"session_{session.id}_{uuid_lib.uuid4().hex[:8]}{ext}"
    path = upload_dir / name
    content = await file.read()
    path.write_bytes(content)
    photo_url = f"/{settings.upload_photos_dir}/{name}"

    session_photo = SessionPhoto(session_id=session.id, photo_url=photo_url)
    db.add(session_photo)
    await db.flush()
    return {"photo_url": photo_url, "id": str(session_photo.id)}


@router.post("/me/session/video")
async def upload_session_video(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_session),
    current_user=Depends(require_roles(UserRole.CANDIDATE)),
):
    """Upload recorded interview video (video mode)."""
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be a video")
    user_id = UUID(current_user["sub"])
    session_result = await db.execute(
        select(InterviewSession)
        .where(InterviewSession.candidate_id == user_id)
        .where(InterviewSession.status == "active")
        .order_by(InterviewSession.started_at.desc())
        .limit(1)
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active session")

    settings = get_settings()
    upload_dir = Path(settings.upload_videos_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "video").suffix or ".webm"
    name = f"session_{session.id}{ext}"
    path = upload_dir / name
    content = await file.read()
    path.write_bytes(content)
    video_url = f"/{settings.upload_videos_dir}/{name}"
    session.video_url = video_url
    await db.flush()
    return {"video_url": video_url}
