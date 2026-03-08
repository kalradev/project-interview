"""Schemas for candidates (admin import, list, report, action)."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class CandidateCreate(BaseModel):
    """Import a candidate (from Naukri/manual/CSV)."""

    email: EmailStr
    full_name: Optional[str] = None
    job_role: str
    tech_stack: Optional[list[str]] = None
    resume_text: Optional[str] = None
    resume_url: Optional[str] = None
    links: Optional[list[str]] = None
    projects: Optional[list[str]] = None
    certificates: Optional[list[str]] = None
    experience: Optional[list[str]] = None
    source: str = "manual"
    interview_scheduled_at: Optional[datetime] = None
    send_email: bool = True
    ats_score: Optional[float] = None  # When > 60, invite email is sent to candidate regardless of send_email
    matched_skills: Optional[list[str]] = None  # Stored in candidate details (ATS analysis)
    missing_skills: Optional[list[str]] = None
    suggestions: Optional[list[str]] = None


class CandidateResponse(BaseModel):
    """Candidate in admin list."""

    id: UUID
    user_id: UUID
    email: str
    full_name: Optional[str] = None
    job_role: str
    tech_stack: Optional[list[str]] = None
    links: Optional[list[str]] = None
    projects: Optional[list[str]] = None
    certificates: Optional[list[str]] = None
    experience: Optional[list[str]] = None
    source: str
    status: str
    ats_score: Optional[float] = None
    ats_details: Optional[dict] = None  # { matched_skills, missing_skills, suggestions }
    interview_scheduled_at: Optional[datetime] = None
    invited_at: Optional[datetime] = None
    photo_url: Optional[str] = None
    created_at: datetime
    resume_text: Optional[str] = None
    resume_url: Optional[str] = None

    model_config = {"from_attributes": True}


class CandidateImportResponse(BaseModel):
    """Response when importing a candidate: candidate data + whether invite email was sent."""

    candidate: CandidateResponse
    email_sent: bool  # True if invite email was successfully sent (or send_email was False)
    email_error: Optional[str] = None  # Reason when email_sent is False (e.g. Brevo/SMTP failure)


class ResumeExtractRequest(BaseModel):
    """Request to extract details from resume text for form pre-fill."""

    resume_text: str
    job_description: str = ""  # Optional; when provided, ATS score is computed against it


class ResumeExtractResponse(BaseModel):
    """Extracted resume details for form (edit and save to DB)."""

    email: str = ""
    full_name: str = ""
    job_role: str = ""
    tech_stack: list[str] = []
    links: list[str] = []  # flat list (all platforms combined)
    links_github: list[str] = []
    links_linkedin: list[str] = []
    links_portfolio: list[str] = []
    links_other: list[str] = []
    projects: list[str] = []
    certificates: list[str] = []
    experience: list[str] = []
    resume_text: str = ""
    ats_score: float = 0.0  # 0–100; computed dynamically from resume + job description
    matched_skills: list[str] = []  # Skills from job description found in resume
    missing_skills: list[str] = []  # Skills from job description not found in resume
    suggestions: list[str] = []  # Improvement suggestions for the candidate


class ResumeFromPlatformRequest(BaseModel):
    """Resume submitted from job platform. Email extracted from resume; shortlist if ATS >= 85."""

    resume_text: str
    job_role: str
    full_name: Optional[str] = None
    tech_stack: Optional[list[str]] = None


class ResumeFromPlatformResponse(BaseModel):
    """Result of platform resume submission."""

    shortlisted: bool  # True if ATS score >= 85 and candidate was created
    ats_score: float
    email: Optional[str] = None  # Extracted from resume
    message: str
    candidate_id: Optional[UUID] = None


class CandidateAction(BaseModel):
    """Admin action: allow next round, select, or reject."""

    status: str  # next_round, selected, rejected


class InterviewExchangeResponse(BaseModel):
    """One Q&A in the report."""

    question_index: int
    question_text: str
    answer_text: str
    created_at: datetime


class SessionPhotoResponse(BaseModel):
    """One photo captured during interview."""

    id: UUID
    photo_url: str
    captured_at: datetime


class AgentReportBlock(BaseModel):
    """Agent assessment (accuracy, communication, summary) for admin."""

    accuracy_score: Optional[float] = None  # 0-100
    communication_score: Optional[float] = None  # 0-100
    summary: Optional[str] = None
    interrupt_count: int = 0  # Times user cut agent


class InterviewReportResponse(BaseModel):
    """Full interview report for admin (Q&A, photos, video, agent result, face/lip check)."""

    session_id: UUID
    candidate_id: UUID
    candidate_email: str
    job_role: str
    exchanges: list[InterviewExchangeResponse]
    summary: Optional[str] = None
    integrity_score: Optional[float] = None
    integrity_risk: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    photo_url: Optional[str] = None  # Before-interview photo (profile)
    session_photos: list[SessionPhotoResponse] = []  # During-interview photos
    video_url: Optional[str] = None  # Recorded interview video
    agent_report: Optional[AgentReportBlock] = None  # Accuracy, communication, summary, interrupt count
    face_lip_status: Optional[str] = None  # pass | review | pending (cheating check)
