"""Schemas for OpenAI-powered interview (next question, conversation)."""

from typing import Optional

from pydantic import BaseModel


class Exchange(BaseModel):
    """One Q&A exchange in the interview."""

    question: str
    answer: str


class NextQuestionRequest(BaseModel):
    """Request next interview question (first or follow-up)."""

    job_role: str
    tech_stack: Optional[list[str]] = None  # e.g. ["Python", "React"] for role-specific + tech questions
    previous_exchanges: list[Exchange] = []


class NextQuestionResponse(BaseModel):
    """Response with the next question from the AI interviewer."""

    question: str
    question_index: int


class RecordExchangeRequest(BaseModel):
    """Store one Q&A for admin report."""

    session_id: str  # UUID as string
    question_index: int
    question_text: str
    answer_text: str
    answered_quickly: Optional[bool] = False  # True if user submitted before reading (cut agent)
