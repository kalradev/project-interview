"""Admin routes - import candidates, list, report, allow/select/reject."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_roles
from app.auth.jwt import get_current_user_required
from app.database import get_async_session
from app.models.candidate_profile import CandidateProfile
from app.models.interview_exchange import InterviewExchange
from app.models.interview_session import InterviewSession
from app.models.session_photo import SessionPhoto
from app.models.user import User, UserRole
from app.schemas.candidate import (
    AgentReportBlock,
    CandidateAction,
    CandidateCreate,
    CandidateResponse,
    InterviewExchangeResponse,
    InterviewReportResponse,
    SessionPhotoResponse,
)
from app.services.candidate_service import (
    add_candidate,
    get_candidates,
    update_candidate_status,
)

router = APIRouter()


def _candidate_to_response(profile: CandidateProfile, email: str, full_name: str | None) -> CandidateResponse:
    return CandidateResponse(
        id=profile.id,
        user_id=profile.user_id,
        email=email,
        full_name=full_name,
        job_role=profile.job_role,
        tech_stack=profile.tech_stack,
        links=getattr(profile, "links", None),
        projects=getattr(profile, "projects", None),
        certificates=getattr(profile, "certificates", None),
        experience=getattr(profile, "experience", None),
        source=profile.source,
        status=profile.status,
        ats_score=profile.ats_score,
        interview_scheduled_at=profile.interview_scheduled_at,
        invited_at=profile.invited_at,
        photo_url=profile.photo_url,
        created_at=profile.created_at,
    )


@router.post("", response_model=CandidateResponse)
async def import_candidate(
    payload: CandidateCreate,
    db: AsyncSession = Depends(get_async_session),
    _user=Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER)),
):
    """Import a candidate (from Naukri/manual/CSV). Creates user, sends invite email with password and interview time."""
    try:
        user, profile, _ = await add_candidate(
            db,
            email=payload.email,
            full_name=payload.full_name,
            job_role=payload.job_role,
            tech_stack=payload.tech_stack,
            resume_text=payload.resume_text,
            resume_url=payload.resume_url,
            links=payload.links,
            projects=payload.projects,
            certificates=payload.certificates,
            experience=payload.experience,
            source=payload.source,
            interview_scheduled_at=payload.interview_scheduled_at,
            send_email=payload.send_email,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return _candidate_to_response(profile, user.email, user.full_name)


@router.get("", response_model=list[CandidateResponse])
async def list_candidates(
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_async_session),
    _user=Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER)),
):
    """List all candidates, optionally filter by status."""
    rows = await get_candidates(db, status=status, limit=limit, offset=offset)
    return [
        _candidate_to_response(profile, user.email, user.full_name)
        for profile, user in rows
    ]


@router.get("/{candidate_id}/report", response_model=InterviewReportResponse | None)
async def get_candidate_report(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    _user=Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER)),
):
    """Get full interview report for a candidate (last session: exchanges + summary + integrity)."""
    profile_result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.id == candidate_id)
    )
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    user_result = await db.execute(select(User).where(User.id == profile.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    session_result = await db.execute(
        select(InterviewSession)
        .where(InterviewSession.candidate_id == profile.user_id)
        .order_by(InterviewSession.started_at.desc())
        .limit(1)
    )
    session = session_result.scalar_one_or_none()
    if not session:
        return None

    exchanges_result = await db.execute(
        select(InterviewExchange)
        .where(InterviewExchange.session_id == session.id)
        .order_by(InterviewExchange.question_index)
    )
    exchanges = exchanges_result.scalars().all()

    from app.models.integrity_score import IntegrityScore
    score_result = await db.execute(
        select(IntegrityScore)
        .where(IntegrityScore.session_id == session.id)
        .order_by(IntegrityScore.computed_at.desc())
        .limit(1)
    )
    score_row = score_result.scalar_one_or_none()

    photos_result = await db.execute(
        select(SessionPhoto)
        .where(SessionPhoto.session_id == session.id)
        .order_by(SessionPhoto.captured_at)
    )
    session_photos = photos_result.scalars().all()

    return InterviewReportResponse(
        session_id=session.id,
        candidate_id=profile.id,
        candidate_email=user.email,
        job_role=profile.job_role,
        exchanges=[
            InterviewExchangeResponse(
                question_index=e.question_index,
                question_text=e.question_text,
                answer_text=e.answer_text,
                created_at=e.created_at,
            )
            for e in exchanges
        ],
        summary=session.interview_summary,
        integrity_score=float(score_row.score) if score_row else None,
        integrity_risk=score_row.risk_level if score_row else None,
        started_at=session.started_at,
        ended_at=session.ended_at,
        photo_url=profile.photo_url,
        session_photos=[
            SessionPhotoResponse(id=p.id, photo_url=p.photo_url, captured_at=p.captured_at)
            for p in session_photos
        ],
        video_url=session.video_url,
        agent_report=AgentReportBlock(
            accuracy_score=session.agent_report.get("accuracy_score"),
            communication_score=session.agent_report.get("communication_score"),
            summary=session.agent_report.get("summary"),
            interrupt_count=session.agent_report.get("interrupt_count", 0),
        ) if session.agent_report else None,
        face_lip_status=session.face_lip_status,
    )


@router.post("/{candidate_id}/action", response_model=CandidateResponse)
async def candidate_action(
    candidate_id: UUID,
    payload: CandidateAction,
    db: AsyncSession = Depends(get_async_session),
    _user=Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER)),
):
    """Admin action: set status to next_round, selected, or rejected."""
    if payload.status not in ("next_round", "selected", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="status must be next_round, selected, or rejected",
        )
    profile = await update_candidate_status(db, candidate_id, payload.status)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    user_result = await db.execute(select(User).where(User.id == profile.user_id))
    user = user_result.scalar_one()
    return _candidate_to_response(profile, user.email, user.full_name)
