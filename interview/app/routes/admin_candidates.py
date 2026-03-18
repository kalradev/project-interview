"""Admin routes - import candidates, list, report, allow/select/reject."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

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
    CandidateImportResponse,
    CandidateResponse,
    InterviewExchangeResponse,
    InterviewReportResponse,
    SessionPhotoResponse,
)
from app.services.candidate_service import (
    add_candidate,
    delete_candidate,
    get_candidates,
    update_candidate_status,
)

router = APIRouter()


def _candidate_to_response(
    profile: CandidateProfile,
    email: str,
    full_name: str | None,
    *,
    include_resume: bool = False,
) -> CandidateResponse:
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
        ats_details=getattr(profile, "ats_details", None),
        interview_scheduled_at=profile.interview_scheduled_at,
        invited_at=profile.invited_at,
        photo_url=profile.photo_url,
        created_at=profile.created_at,
        resume_text=profile.resume_text if include_resume else None,
        resume_url=profile.resume_url if include_resume else None,
    )


@router.post("", response_model=CandidateImportResponse)
async def import_candidate(
    payload: CandidateCreate,
    db: AsyncSession = Depends(get_async_session),
    _user=Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER)),
):
    """Import a candidate (from Naukri/manual/CSV). Creates user. When ATS score > 60, invite email is sent to the candidate's email; otherwise respects send_email toggle. ATS details (matched/missing skills, suggestions) are stored in candidate details."""
    ats = payload.ats_score
    send_invite = payload.send_email or (ats is not None and ats > 60)
    ats_details = None
    if payload.matched_skills is not None or payload.missing_skills is not None or payload.suggestions is not None:
        ats_details = {
            "matched_skills": payload.matched_skills or [],
            "missing_skills": payload.missing_skills or [],
            "suggestions": payload.suggestions or [],
        }
    try:
        user, profile, _, email_sent, email_error = await add_candidate(
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
            send_email=send_invite,
            ats_score=ats,
            ats_details=ats_details,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return CandidateImportResponse(
        candidate=_candidate_to_response(profile, user.email, user.full_name),
        email_sent=email_sent,
        email_error=email_error or None,
    )


@router.get("", response_model=list[CandidateResponse])
async def list_candidates(
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_async_session),
    _user=Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER)),
):
    """List all candidates, optionally filter by status. Optimized for fast loading."""
    import asyncio
    import time
    start_time = time.time()
    try:
        # Add timeout to prevent slow queries
        rows = await asyncio.wait_for(
            get_candidates(db, status=status, limit=limit, offset=offset),
            timeout=3.0,  # 3 second timeout for list queries
        )
        result = [
            _candidate_to_response(profile, user.email, user.full_name)
            for profile, user in rows
        ]
        elapsed = time.time() - start_time
        if elapsed > 1.0:  # Log if query takes more than 1 second
            logger.warning(f"List candidates query took {elapsed:.2f}s (status={status}, limit={limit})")
        return result
    except asyncio.TimeoutError:
        logger.error(f"List candidates query timed out after 3 seconds (status={status})")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database query timeout. Please try again.",
        )


@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    _user=Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER)),
):
    """Get a single candidate by id (for profile page). Optimized with join."""
    import asyncio
    try:
        # Use join to fetch both in one query for better performance
        result = await asyncio.wait_for(
            db.execute(
                select(CandidateProfile, User)
                .join(User, CandidateProfile.user_id == User.id)
                .where(CandidateProfile.id == candidate_id)
            ),
            timeout=2.0,  # 2 second timeout
        )
        row = result.first()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
        profile, user = row
        return _candidate_to_response(profile, user.email, user.full_name, include_resume=True)
    except asyncio.TimeoutError:
        logger.error(f"Get candidate query timed out for {candidate_id}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database query timeout. Please try again.",
        )


@router.get("/{candidate_id}/report", response_model=InterviewReportResponse | None)
async def get_candidate_report(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    _user=Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER)),
):
    """Get full interview report for a candidate (last session: exchanges + summary + integrity). Optimized with parallel queries."""
    import asyncio
    import time
    start_time = time.time()
    try:
        # First, get profile and user in one query
        profile_user_result = await asyncio.wait_for(
            db.execute(
                select(CandidateProfile, User)
                .join(User, CandidateProfile.user_id == User.id)
                .where(CandidateProfile.id == candidate_id)
            ),
            timeout=2.0,
        )
        row = profile_user_result.first()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
        profile, user = row

        # Get the latest session
        session_result = await asyncio.wait_for(
            db.execute(
                select(InterviewSession)
                .where(InterviewSession.candidate_id == profile.user_id)
                .order_by(InterviewSession.started_at.desc())
                .limit(1)
            ),
            timeout=2.0,
        )
        session = session_result.scalar_one_or_none()
        if not session:
            return None

        # Execute all remaining queries in parallel for better performance
        from app.models.integrity_score import IntegrityScore
        
        exchanges_task = asyncio.wait_for(
            db.execute(
                select(InterviewExchange)
                .where(InterviewExchange.session_id == session.id)
                .order_by(InterviewExchange.question_index)
            ),
            timeout=2.0,
        )
        
        score_task = asyncio.wait_for(
            db.execute(
                select(IntegrityScore)
                .where(IntegrityScore.session_id == session.id)
                .order_by(IntegrityScore.computed_at.desc())
                .limit(1)
            ),
            timeout=2.0,
        )
        
        photos_task = asyncio.wait_for(
            db.execute(
                select(SessionPhoto)
                .where(SessionPhoto.session_id == session.id)
                .order_by(SessionPhoto.captured_at)
            ),
            timeout=2.0,
        )

        # Wait for all queries to complete in parallel
        exchanges_result, score_result, photos_result = await asyncio.gather(
            exchanges_task, score_task, photos_task
        )
        
        exchanges = exchanges_result.scalars().all()
        score_row = score_result.scalar_one_or_none()
        session_photos = photos_result.scalars().all()
        
        elapsed = time.time() - start_time
        if elapsed > 2.0:  # Log if report takes more than 2 seconds
            logger.warning(f"Get candidate report took {elapsed:.2f}s for {candidate_id}")
        
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
                accuracy_score=session.agent_report.get("accuracy_score") if session.agent_report else None,
                communication_score=session.agent_report.get("communication_score") if session.agent_report else None,
                summary=session.agent_report.get("summary") if session.agent_report else None,
                interrupt_count=session.agent_report.get("interrupt_count", 0) if session.agent_report else 0,
            ) if session.agent_report else None,
            face_lip_status=session.face_lip_status,
        )
    except asyncio.TimeoutError:
        elapsed = time.time() - start_time if 'start_time' in locals() else 0
        logger.error(f"Get candidate report timed out after 2 seconds (total: {elapsed:.2f}s) for {candidate_id}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database query timeout. Please try again.",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Get candidate report failed for {candidate_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load report. Please try again.",
        )

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


@router.delete("/{candidate_id}")
async def delete_candidate_route(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    _user=Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER)),
):
    """Delete a candidate (profile, user, and all their interview sessions)."""
    deleted = await delete_candidate(db, candidate_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return {"ok": True}
