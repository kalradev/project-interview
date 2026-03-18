"""Exam / interview link routes - token validation for browser-based interview."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_async_session
from app.models.user import User, UserRole
from app.auth.jwt import decode_interview_link_token, create_access_token
from app.services.session_service import SessionService
from app.config import get_settings

router = APIRouter()
session_service = SessionService()


class ExamValidateRequest(BaseModel):
    token: str


class ExamValidateResponse(BaseModel):
    access_token: str
    session_id: str
    session_token: str
    api_base_url: str


@router.post("/validate", response_model=ExamValidateResponse)
async def validate_exam_link(
    payload: ExamValidateRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Validate interview link token from email. Returns access token and session
    so the frontend can start the browser-based exam without showing login.
    """
    payload_decoded = decode_interview_link_token(payload.token)
    user_id = UUID(payload_decoded["sub"])

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account inactive")
    if user.role != UserRole.CANDIDATE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a candidate account")

    session = await session_service.get_or_create_for_candidate(db, user_id)
    await db.commit()

    access_token = create_access_token(subject=user.id, role=user.role)
    settings = get_settings()
    api_base_url = (settings.api_public_url or "").strip() or ""

    return ExamValidateResponse(
        access_token=access_token,
        session_id=str(session.id),
        session_token=session.session_token,
        api_base_url=api_base_url,
    )
