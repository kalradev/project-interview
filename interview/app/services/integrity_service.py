"""Integrity service - compute and persist integrity score."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.integrity_engine import IntegrityEngine
from app.models.integrity_score import IntegrityScore
from app.services.event_service import EventService


class IntegrityService:
    """Compute integrity score from events and AI probability; persist and cache."""

    def __init__(self) -> None:
        self.engine = IntegrityEngine()
        self.event_service = EventService()

    async def compute_and_save(
        self,
        db: AsyncSession,
        session_id: UUID,
        ai_probability: float = 0.0,
    ) -> IntegrityScore:
        """Get event counts, compute score, and persist IntegrityScore."""
        event_counts = await self.event_service.get_event_counts_by_session(db, session_id)
        score, risk, penalties = self.engine.compute(event_counts, ai_probability)
        integrity = IntegrityScore(
            session_id=session_id,
            score=score,
            risk_level=risk,
            penalties=penalties,
        )
        db.add(integrity)
        await db.flush()
        await db.refresh(integrity)
        return integrity
