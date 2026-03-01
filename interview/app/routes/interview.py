"""Interview routes - AI-generated questions by job role (OpenAI), record Q&A."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_user_required
from app.database import get_async_session
from app.models.interview_exchange import InterviewExchange
from app.models.interview_session import InterviewSession
from app.schemas.interview import NextQuestionRequest, NextQuestionResponse, RecordExchangeRequest
from app.services.openai_interview_service import OpenAIInterviewService
from sqlalchemy import select

router = APIRouter()
interview_service = OpenAIInterviewService()


@router.get("/status")
async def interview_status(
    current_user=Depends(get_current_user_required),
) -> dict:
    """Check if the OpenAI interview agent is available (API key configured)."""
    return {"openai_configured": interview_service.is_available()}


@router.post("/next-question", response_model=NextQuestionResponse)
async def get_next_question(
    payload: NextQuestionRequest,
    current_user=Depends(get_current_user_required),
):
    """
    Get the next interview question from the AI.
    Send job_role and optional previous_exchanges (list of {question, answer}).
    Returns the next question and its index (0-based).
    """
    previous = [{"question": e.question, "answer": e.answer} for e in payload.previous_exchanges]
    question = await interview_service.get_next_question(
        job_role=payload.job_role,
        previous_exchanges=previous,
        tech_stack=payload.tech_stack or None,
    )
    return NextQuestionResponse(
        question=question,
        question_index=len(payload.previous_exchanges),
    )


@router.post("/record-exchange")
async def record_exchange(
    payload: RecordExchangeRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user=Depends(get_current_user_required),
):
    """Store one question-answer pair for the admin report (call after each answer submit)."""
    try:
        session_id = UUID(payload.session_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid session_id")
    result = await db.execute(select(InterviewSession).where(InterviewSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if str(session.candidate_id) != str(current_user["sub"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your session")
    exchange = InterviewExchange(
        session_id=session_id,
        question_index=payload.question_index,
        question_text=payload.question_text,
        answer_text=payload.answer_text,
        answered_quickly=payload.answered_quickly or False,
    )
    db.add(exchange)
    await db.flush()
    return {"id": str(exchange.id)}
