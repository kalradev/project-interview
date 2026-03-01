"""Generate agent report (accuracy, communication, summary) and face/lip status when session ends."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview_exchange import InterviewExchange
from app.models.interview_session import InterviewSession
from app.models.session_photo import SessionPhoto
from app.services.openai_interview_service import OpenAIInterviewService


async def fill_agent_report_on_session_end(
    db: AsyncSession,
    session_id: UUID,
) -> None:
    """
    After session ends: generate agent report (accuracy, communication, summary) from exchanges,
    set face_lip_status from session photos, and save on session.
    """
    result = await db.execute(select(InterviewSession).where(InterviewSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        return

    # Load exchanges and count interrupts (user cut agent)
    ex_result = await db.execute(
        select(InterviewExchange)
        .where(InterviewExchange.session_id == session_id)
        .order_by(InterviewExchange.question_index)
    )
    exchanges = ex_result.scalars().all()
    interrupt_count = sum(1 for e in exchanges if getattr(e, "answered_quickly", False))

    job_role = "Candidate"
    if session.metadata_ and isinstance(session.metadata_, dict):
        job_role = session.metadata_.get("job_role") or job_role

    # Generate agent report via OpenAI
    report = None
    if exchanges:
        service = OpenAIInterviewService()
        report = await service.generate_agent_report(
            job_role=job_role,
            exchanges=[{"question": e.question_text, "answer": e.answer_text} for e in exchanges],
            interrupt_count=interrupt_count,
        )
    if report:
        report["interrupt_count"] = interrupt_count
        session.agent_report = report
    else:
        session.agent_report = {
            "accuracy_score": None,
            "communication_score": None,
            "summary": "Report could not be generated (no OpenAI or no exchanges).",
            "interrupt_count": interrupt_count,
        }

    # Face/lip status: pass if we have session photos (face assumed visible), else review/pending
    photos_result = await db.execute(
        select(SessionPhoto).where(SessionPhoto.session_id == session_id)
    )
    photos = photos_result.scalars().all()
    if not photos:
        session.face_lip_status = "pending"
    else:
        any_face = any(getattr(p, "face_detected", True) for p in photos)
        session.face_lip_status = "pass" if any_face else "review"

    await db.flush()
