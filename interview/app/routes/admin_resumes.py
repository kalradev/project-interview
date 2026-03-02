"""Admin routes - ingest resume from job platform; shortlist by ATS >= 85, send email."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_roles
from app.database import get_async_session
from app.models.user import UserRole
from app.schemas.candidate import (
    ResumeExtractRequest,
    ResumeExtractResponse,
    ResumeFromPlatformRequest,
    ResumeFromPlatformResponse,
)
from app.services.candidate_service import add_candidate
from app.services.resume_file_service import extract_text_from_resume_file
from app.services.resume_platform_service import (
    compute_ats_score,
    extract_email_from_resume,
    extract_resume_details_async,
    is_shortlisted,
)

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _details_to_response(details: dict) -> ResumeExtractResponse:
    return ResumeExtractResponse(
        email=details.get("email", ""),
        full_name=details.get("full_name", ""),
        job_role=details.get("job_role", ""),
        tech_stack=details.get("tech_stack", []),
        links=details.get("links", []),
        links_github=details.get("links_github", []),
        links_linkedin=details.get("links_linkedin", []),
        links_portfolio=details.get("links_portfolio", []),
        links_other=details.get("links_other", []),
        projects=details.get("projects", []),
        certificates=details.get("certificates", []),
        experience=details.get("experience", []),
        resume_text=details.get("resume_text", ""),
    )


@router.post("/extract", response_model=ResumeExtractResponse)
async def extract_resume(
    payload: ResumeExtractRequest,
    _user=Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER)),
):
    """Extract structured details: preprocess with section markers, then LLM or rule-based parse."""
    details = await extract_resume_details_async(payload.resume_text)
    return _details_to_response(details)


@router.post("/extract-file", response_model=ResumeExtractResponse)
async def extract_resume_file(
    file: UploadFile = File(...),
    _user=Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER)),
):
    """Upload a resume (PDF or DOCX); extract text and return same structured details for form pre-fill."""
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing filename")
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only PDF and DOCX are allowed. Got: {file.filename}",
        )
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File too large (max 10 MB)")
    text = extract_text_from_resume_file(content, file.filename)
    if not text or not text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Could not extract text from this file. "
                "Common causes: scanned/image-only PDF (no selectable text), corrupted file, or empty document. "
                "Use a PDF/DOCX with selectable text, or paste the resume content into the text area instead."
            ),
        )
    details = await extract_resume_details_async(text)
    return _details_to_response(details)


@router.post("/from-platform", response_model=ResumeFromPlatformResponse)
async def resume_from_platform(
    payload: ResumeFromPlatformRequest,
    db: AsyncSession = Depends(get_async_session),
    _user=Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER)),
):
    """
    Ingest resume from job platform. Extract email from resume; compute ATS score.
    If ATS score >= 85, shortlist: create candidate user, send invite email with
    password and interview timing. Otherwise return score and message (not shortlisted).
    """
    email = extract_email_from_resume(payload.resume_text)
    if not email:
        return ResumeFromPlatformResponse(
            shortlisted=False,
            ats_score=0.0,
            email=None,
            message="No email found in resume. Cannot shortlist.",
            candidate_id=None,
        )

    ats_score = compute_ats_score(payload.resume_text, payload.job_role)
    if not is_shortlisted(ats_score):
        return ResumeFromPlatformResponse(
            shortlisted=False,
            ats_score=ats_score,
            email=email,
            message=f"ATS score {ats_score} is below 85. Not shortlisted.",
            candidate_id=None,
        )

    try:
        user, profile, _, _email_sent, _ = await add_candidate(
            db,
            email=email,
            full_name=payload.full_name,
            job_role=payload.job_role,
            tech_stack=payload.tech_stack,
            resume_text=payload.resume_text,
            resume_url=None,
            source="platform",
            interview_scheduled_at=None,
            send_email=True,
            ats_score=ats_score,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return ResumeFromPlatformResponse(
        shortlisted=True,
        ats_score=ats_score,
        email=email,
        message="Shortlisted. Candidate created and invite email sent with password and interview timing.",
        candidate_id=profile.id,
    )
