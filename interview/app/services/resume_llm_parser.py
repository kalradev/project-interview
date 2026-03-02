"""
LLM-based resume parser using strict JSON schema.
Uses preprocessed text with [SECTION: X] markers for high accuracy.
Returns structured data; mapped to our extract dict for form pre-fill.
"""

import json
import logging
import re
from typing import Any

from app.config import get_settings
from app.services.resume_platform_service import is_education_line

logger = logging.getLogger(__name__)

SECTION_MARKER_PATTERN = re.compile(r"\[SECTION:\s*[^\]]*\]\s*", re.IGNORECASE)


def _strip_section_marker(s: str) -> str:
    """Remove [SECTION: ...] from extracted values so they never leak into the form."""
    if not s or not isinstance(s, str):
        return s
    return SECTION_MARKER_PATTERN.sub("", s).strip()

RESUME_PARSER_SYSTEM = """You are a resume parsing engine designed to handle resumes with inconsistent or custom section headings.

Your job is to:
1. Detect section headings even if their names vary.
2. Normalize all detected headings into a fixed internal schema.
3. Extract content strictly under the correct normalized section.
4. Never mix content across sections.
5. Handle multi-column layouts and bullet lists accurately.
6. Do NOT infer or fabricate missing data.
7. Preserve original wording.
8. Return ONLY valid JSON.

You must internally normalize headings before extraction."""

RESUME_PARSER_USER_TEMPLATE = """Parse the resume text below.

Step 1: Identify section headings even if written differently. Use the following normalization map.

HEADING NORMALIZATION MAP (examples, not exhaustive):

Summary: Profile, Professional Summary, About Me, Career Objective, Overview

Experience: Work Experience, Employment History, Professional Experience, Industry Experience

Internships: Internship, Intern Experience, Training, Apprenticeship

Projects: Projects, Personal Projects, Academic Projects, Key Projects

Skills: Skills, Technical Skills, Tech Stack, Core Competencies, Expertise

Education: Education, Academic Background, Qualifications

Certifications: Certifications, Courses, Licenses, Training & Certifications

Links: Links, Profiles, Online Presence

Hobbies: Hobbies, Interests, Extracurricular Activities

Step 2: Extract data ONLY after normalization. Never mix content across sections.
Step 3: Return data in the strict JSON schema below.

Critical rules:
- Projects = standalone projects (side projects, academic projects, open source). Do NOT put work experience or job responsibilities in projects. Each project is one object with name, description, technologies. Extract EVERY project listed on the resume with no omission; each project will be shown in its own column.
- Experience = employment history only (role, company, dates, responsibilities). Bullets under a job belong to that job only. Extract EVERY experience/internship entry with no omission; each entry will be shown in its own column.
- Extract ALL skills and technologies listed (every language, framework, tool).
- Extract ALL links with full URLs (GitHub, LinkedIn, portfolio, etc.). Use complete URLs only.

JSON Schema (STRICT):
{
  "full_name": string,
  "job_title": string,
  "contact": {
    "email": string,
    "phone": string,
    "location": string
  },
  "summary": string,
  "links": {
    "github": string,
    "linkedin": string,
    "leetcode": string,
    "portfolio": string,
    "other": [string]
  },
  "skills": [string],
  "experience": [
    {
      "role": string,
      "company": string,
      "location": string,
      "start_date": string,
      "end_date": string,
      "responsibilities": [string]
    }
  ],
  "internships": [
    {
      "role": string,
      "company": string,
      "location": string,
      "start_date": string,
      "end_date": string,
      "responsibilities": [string]
    }
  ],
  "projects": [
    {
      "name": string,
      "description": string,
      "technologies": [string]
    }
  ],
  "education": [
    {
      "degree": string,
      "institution": string,
      "location": string,
      "start_year": string,
      "end_year": string
    }
  ],
  "certifications": [string],
  "hobbies": [string]
}

Resume Text:
<<<PASTE PREPROCESSED TEXT HERE>>>
"""


def _parse_llm_json(response_text: str) -> dict[str, Any] | None:
    """Extract JSON from LLM response (strip markdown code block if present)."""
    text = response_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning("LLM resume JSON parse error: %s", e)
        return None


def _llm_result_to_extract_dict(data: dict[str, Any], original_text: str) -> dict[str, Any]:
    """Map LLM schema to our extract response dict (form pre-fill)."""
    contact = data.get("contact") or {}
    links_obj = data.get("links") or {}
    skills_data = data.get("skills")
    experience_arr = data.get("experience") or []
    internships_arr = data.get("internships") or []
    projects_arr = data.get("projects") or []
    certifications_arr = data.get("certifications") or []

    email = _strip_section_marker((contact.get("email") or "").strip() or "")
    full_name = _strip_section_marker((data.get("full_name") or "").strip() or "")
    job_role_raw = _strip_section_marker((data.get("job_title") or "").strip() or "")
    # Do not use education text (e.g. college name + CGPA) as job_role
    job_role = "" if is_education_line(job_role_raw) else job_role_raw

    def _valid_link(u: str) -> bool:
        u = (u or "").strip()
        if not u or len(u) < 10:
            return False
        if u.rstrip("/").endswith("/_") or "/_ " in u:
            return False
        return True

    def _normalize_url(u: str) -> str:
        u = (u or "").strip()
        if not u:
            return ""
        u = _strip_section_marker(u)
        if not u.lower().startswith("http"):
            if "github.com" in u.lower():
                u = "https://" + u if not u.startswith("//") else "https:" + u
            elif "linkedin.com" in u.lower():
                u = "https://" + u if not u.startswith("//") else "https:" + u
            else:
                u = "https://" + u
        return u.rstrip(".,;:)")

    links_list = []
    links_github: list[str] = []
    links_linkedin: list[str] = []
    links_portfolio: list[str] = []
    links_other: list[str] = []

    for key in ("github", "linkedin", "leetcode", "portfolio"):
        val = links_obj.get(key)
        if val and isinstance(val, str):
            val = _normalize_url(val)
            if _valid_link(val):
                links_list.append(val)
                if key == "github":
                    links_github.append(val)
                elif key == "linkedin":
                    links_linkedin.append(val)
                elif key == "portfolio":
                    links_portfolio.append(val)
                else:
                    links_other.append(val)
    for u in links_obj.get("other") or []:
        if u and isinstance(u, str):
            u = _normalize_url(u)
            if _valid_link(u):
                links_list.append(u)
                links_other.append(u)

    tech_stack = []
    if isinstance(skills_data, list):
        for s in skills_data:
            if s and isinstance(s, str):
                s = _strip_section_marker(s.strip())
                if s:
                    tech_stack.append(s)
    elif isinstance(skills_data, dict):
        for key in ("frontend", "backend", "databases", "languages", "tools", "other"):
            arr = skills_data.get(key)
            if isinstance(arr, list):
                for s in arr:
                    if s and isinstance(s, str):
                        s = _strip_section_marker(s.strip())
                        if s:
                            tech_stack.append(s)

    # One experience entry per job: each entry is one string (header + bullets joined by newline)
    experience_blocks: list[str] = []
    for item in experience_arr:
        if not isinstance(item, dict):
            continue
        role = _strip_section_marker((item.get("role") or "").strip())
        company = _strip_section_marker((item.get("company") or "").strip())
        start = (item.get("start_date") or "").strip()
        end = (item.get("end_date") or "").strip()
        loc = _strip_section_marker((item.get("location") or "").strip())
        parts = [p for p in [role, company, f"{start} – {end}".strip(" – ") if start or end else None, loc] if p]
        block_lines = [" | ".join(parts)]
        for r in (item.get("responsibilities") or []):
            if r and isinstance(r, str) and r.strip():
                block_lines.append("  • " + _strip_section_marker(r.strip()))
        experience_blocks.append("\n".join(block_lines))
    for item in internships_arr:
        if not isinstance(item, dict):
            continue
        role = _strip_section_marker((item.get("role") or "").strip())
        company = _strip_section_marker((item.get("company") or "").strip())
        start = (item.get("start_date") or "").strip()
        end = (item.get("end_date") or "").strip()
        parts = [p for p in [f"Intern: {role}" if role else "Intern", company, f"{start} – {end}".strip(" – ") if start or end else None] if p]
        experience_blocks.append(" | ".join(parts))
    experience = experience_blocks[:25]

    project_lines = []
    for item in projects_arr:
        if not isinstance(item, dict):
            continue
        name = _strip_section_marker((item.get("name") or "").strip())
        desc = _strip_section_marker((item.get("description") or "").strip())
        techs = item.get("technologies")
        if not name:
            continue
        line = name
        if desc:
            line += ": " + desc
        if isinstance(techs, list) and techs:
            line += " [" + ", ".join(_strip_section_marker(str(t).strip()) for t in techs if t) + "]"
        project_lines.append(line)
    projects = project_lines[:20]

    certificates = [_strip_section_marker(str(c).strip()) for c in certifications_arr if c and str(c).strip()][:20]

    return {
        "email": email,
        "full_name": full_name,
        "job_role": job_role,
        "tech_stack": tech_stack[:20],
        "links": links_list[:30],
        "links_github": links_github[:5],
        "links_linkedin": links_linkedin[:3],
        "links_portfolio": links_portfolio[:5],
        "links_other": links_other[:10],
        "projects": projects,
        "certificates": certificates,
        "experience": experience,
        "resume_text": original_text,
    }


async def parse_resume_with_llm(preprocessed_text: str, original_text: str) -> dict[str, Any] | None:
    """
    Call OpenAI to parse resume into strict JSON schema; map to our extract dict.
    Returns None if API key missing, call fails, or JSON invalid.
    """
    settings = get_settings()
    if not settings.openai_api_key or not preprocessed_text.strip():
        return None
    prompt = RESUME_PARSER_USER_TEMPLATE.replace("<<<PASTE PREPROCESSED TEXT HERE>>>", preprocessed_text.strip())
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": RESUME_PARSER_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )
        content = (response.choices[0].message.content or "").strip()
        if not content:
            return None
        data = _parse_llm_json(content)
        if not data:
            return None
        return _llm_result_to_extract_dict(data, original_text)
    except Exception as e:
        logger.warning("LLM resume parse failed: %s", e)
        return None
