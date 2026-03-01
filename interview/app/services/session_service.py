"""Session management service - start, end, metadata, unique session ID."""

import secrets
import uuid
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview_session import InterviewSession
from app.schemas.session import SessionCreate


class SessionService:
    """CRUD and lifecycle for interview sessions."""

    @staticmethod
    def _generate_session_token() -> str:
        """Generate unique session token (URL-safe)."""
        return secrets.token_urlsafe(32)

    async def start_session(
        self,
        db: AsyncSession,
        payload: SessionCreate,
    ) -> InterviewSession:
        """Create and persist a new interview session with unique ID and token."""
        session_token = self._generate_session_token()
        session = InterviewSession(
            session_token=session_token,
            candidate_id=payload.candidate_id,
            interviewer_id=payload.interviewer_id,
            metadata_=payload.metadata,
            status="active",
        )
        db.add(session)
        await db.flush()
        await db.refresh(session)
        return session

    async def get_by_id(self, db: AsyncSession, session_id: UUID) -> Optional[InterviewSession]:
        """Get session by primary key."""
        result = await db.execute(select(InterviewSession).where(InterviewSession.id == session_id))
        return result.scalar_one_or_none()

    async def get_by_token(self, db: AsyncSession, token: str) -> Optional[InterviewSession]:
        """Get session by session_token."""
        result = await db.execute(
            select(InterviewSession).where(InterviewSession.session_token == token)
        )
        return result.scalar_one_or_none()

    async def end_session(
        self,
        db: AsyncSession,
        session_id: UUID,
    ) -> Optional[InterviewSession]:
        """End session by setting ended_at and status."""
        from datetime import datetime, timezone

        session = await self.get_by_id(db, session_id)
        if not session:
            return None
        session.ended_at = datetime.now(timezone.utc)
        session.status = "ended"
        await db.flush()
        await db.refresh(session)
        return session
