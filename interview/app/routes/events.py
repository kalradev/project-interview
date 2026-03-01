"""Event routes - log tab switch, paste, copy, DevTools, idle; typing analysis."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.schemas.events import EventLogRequest, EventLogResponse, TypingEventRequest, AnalyzeAnswerRequest
from app.services.event_service import EventService
from app.services.answer_analysis_service import AnswerAnalysisService
from app.auth.jwt import get_current_user_required

router = APIRouter()
event_service = EventService()
answer_service = AnswerAnalysisService()


@router.post("/log", response_model=EventLogResponse)
async def log_event(
    payload: EventLogRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user=Depends(get_current_user_required),
):
    """Log a suspicious event (tab switch, paste, copy, DevTools, idle, etc.)."""
    event = await event_service.log_event(db, payload)
    return EventLogResponse(
        id=event.id,
        session_id=event.session_id,
        event_type=event.event_type,
        occurred_at=event.occurred_at,
        severity=event.severity,
    )


@router.post("/typing")
async def submit_typing(
    payload: TypingEventRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user=Depends(get_current_user_required),
):
    """Submit keystroke timestamps and optional text for typing analysis (WPS, burst, instant input)."""
    word_count = payload.text_length // 5  # rough proxy if no text
    analysis = answer_service.analyze_typing(
        payload.keystroke_timestamps,
        payload.text_length,
        word_count,
    )
    return {"analysis": analysis}


@router.post("/analyze-answer")
async def analyze_answer(
    payload: AnalyzeAnswerRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user=Depends(get_current_user_required),
):
    """Analyze answer text (AI probability) and optional keystrokes; persist AnswerAnalysis and log burst/instant events."""
    analysis = await answer_service.create_analysis(
        db,
        session_id=payload.session_id,
        answer_text=payload.answer_text or None,
        keystroke_timestamps=payload.keystroke_timestamps,
        question_id=payload.question_id,
        event_service=event_service,
    )
    return {
        "id": str(analysis.id),
        "words_per_second": analysis.words_per_second,
        "ai_probability": analysis.ai_probability,
        "features": analysis.features,
    }
