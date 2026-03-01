"""Event service - log tab switch, paste, copy, DevTools, idle, typing events."""

from collections import defaultdict
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.suspicious_event import EventType, SuspiciousEvent
from app.schemas.events import EventLogRequest


class EventService:
    """Log and query suspicious events."""

    async def log_event(
        self,
        db: AsyncSession,
        payload: EventLogRequest,
    ) -> SuspiciousEvent:
        """Persist a timestamped suspicious event."""
        event = SuspiciousEvent(
            session_id=payload.session_id,
            event_type=payload.event_type,
            payload=payload.payload,
            severity=payload.severity or "medium",
        )
        db.add(event)
        await db.flush()
        await db.refresh(event)
        return event

    async def get_event_counts_by_session(
        self,
        db: AsyncSession,
        session_id: UUID,
    ) -> dict[str, int]:
        """Return counts per event_type for a session (for integrity scoring)."""
        result = await db.execute(
            select(SuspiciousEvent.event_type, func.count(SuspiciousEvent.id))
            .where(SuspiciousEvent.session_id == session_id)
            .group_by(SuspiciousEvent.event_type)
        )
        counts = defaultdict(int)
        for row in result:
            counts[row[0].value] = row[1]
        return dict(counts)
