"""Session routes - start, end, get session, update summary."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.schemas.session import SessionCreate, SessionResponse, SessionEnd, SessionSummaryUpdate
from app.services.session_service import SessionService
from app.services.agent_report_service import fill_agent_report_on_session_end
from app.auth.jwt import get_current_user_required
from app.auth.dependencies import require_roles
from app.models.user import UserRole

router = APIRouter()
session_service = SessionService()


@router.post("", response_model=SessionResponse)
async def start_session(
    payload: SessionCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER)),
):
    """Start a new interview session; returns session with unique session_id and token."""
    session = await session_service.start_session(db, payload)
    return SessionResponse(
        id=session.id,
        session_token=session.session_token,
        candidate_id=session.candidate_id,
        interviewer_id=session.interviewer_id,
        started_at=session.started_at,
        ended_at=session.ended_at,
        status=session.status,
        metadata=session.metadata_,
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user=Depends(get_current_user_required),
):
    """Get session by ID."""
    session = await session_service.get_by_id(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return SessionResponse(
        id=session.id,
        session_token=session.session_token,
        candidate_id=session.candidate_id,
        interviewer_id=session.interviewer_id,
        started_at=session.started_at,
        ended_at=session.ended_at,
        status=session.status,
        metadata=session.metadata_,
    )


@router.post("/end", response_model=SessionResponse)
async def end_session(
    payload: SessionEnd,
    db: AsyncSession = Depends(get_async_session),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER)),
):
    """End an interview session (Admin/Interviewer)."""
    session = await session_service.end_session(db, payload.session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return SessionResponse(
        id=session.id,
        session_token=session.session_token,
        candidate_id=session.candidate_id,
        interviewer_id=session.interviewer_id,
        started_at=session.started_at,
        ended_at=session.ended_at,
        status=session.status,
        metadata=session.metadata_,
    )


@router.post("/end-my", response_model=SessionResponse)
async def end_my_session(
    payload: SessionEnd,
    db: AsyncSession = Depends(get_async_session),
    current_user=Depends(get_current_user_required),
):
    """Candidate ends their own interview session. Agent report and face/lip status are generated."""
    session = await session_service.get_by_id(db, payload.session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if str(session.candidate_id) != str(current_user["sub"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your session")
    session = await session_service.end_session(db, payload.session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    await fill_agent_report_on_session_end(db, payload.session_id)
    await db.refresh(session)
    return SessionResponse(
        id=session.id,
        session_token=session.session_token,
        candidate_id=session.candidate_id,
        interviewer_id=session.interviewer_id,
        started_at=session.started_at,
        ended_at=session.ended_at,
        status=session.status,
        metadata=session.metadata_,
    )


@router.patch("/{session_id}/summary")
async def update_session_summary(
    session_id: UUID,
    payload: SessionSummaryUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user=Depends(get_current_user_required),
):
    """Set interview summary (candidate or admin). Candidate can only update their own session."""
    session = await session_service.get_by_id(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    is_candidate = str(session.candidate_id) == str(current_user["sub"])
    if not is_candidate and current_user["role"] not in (UserRole.ADMIN, UserRole.INTERVIEWER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    session.interview_summary = payload.summary
    await db.flush()
    return {"ok": True}
