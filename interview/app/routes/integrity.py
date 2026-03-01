"""Integrity routes - compute and get integrity score."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.integrity_score import IntegrityScore
from app.schemas.integrity import IntegrityScoreResponse
from app.services.integrity_service import IntegrityService
from app.auth.jwt import get_current_user_required

router = APIRouter()
integrity_service = IntegrityService()


@router.post("/compute/{session_id}", response_model=IntegrityScoreResponse)
async def compute_integrity(
    session_id: UUID,
    ai_probability: float = 0.0,
    db: AsyncSession = Depends(get_async_session),
    current_user=Depends(get_current_user_required),
):
    """Compute integrity score for session (from event counts + optional ai_probability); persist to PostgreSQL."""
    score_record = await integrity_service.compute_and_save(db, session_id, ai_probability)
    return IntegrityScoreResponse(
        id=score_record.id,
        session_id=score_record.session_id,
        score=score_record.score,
        risk_level=score_record.risk_level,
        penalties=score_record.penalties,
        computed_at=score_record.computed_at,
    )


@router.get("/live/{session_id}")
async def get_live_score(
    session_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user=Depends(get_current_user_required),
):
    """Get latest integrity score for session from PostgreSQL."""
    result = await db.execute(
        select(IntegrityScore)
        .where(IntegrityScore.session_id == session_id)
        .order_by(IntegrityScore.computed_at.desc())
        .limit(1)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No score for session")
    return {"score": record.score, "risk": record.risk_level}


@router.get("/{session_id}/history")
async def get_integrity_history(
    session_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user=Depends(get_current_user_required),
):
    """Get all integrity score snapshots for a session."""
    result = await db.execute(
        select(IntegrityScore)
        .where(IntegrityScore.session_id == session_id)
        .order_by(IntegrityScore.computed_at.desc())
    )
    records = result.scalars().all()
    return [
        IntegrityScoreResponse(
            id=r.id,
            session_id=r.session_id,
            score=r.score,
            risk_level=r.risk_level,
            penalties=r.penalties,
            computed_at=r.computed_at,
        )
        for r in records
    ]
