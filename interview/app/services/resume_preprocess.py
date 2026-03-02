"""
Resume text preprocessing: insert [SECTION: HEADER] markers for better parsing.
Helps both rule-based and LLM parsers maintain correct section boundaries.
"""

import re

# Known section headers (normalized to uppercase for matching)
SECTION_HEADERS = {
    "details", "profile", "summary", "objective", "contact", "personal information",
    "employment history", "work experience", "experience", "professional experience",
    "employment", "internships", "internship",
    "skills", "technical skills", "technologies", "tech stack", "expertise",
    "education", "academic", "qualification", "qualifications",
    "projects", "key projects", "project experience", "personal projects",
    "certifications", "certificate", "certificates", "achievements", "awards",
    "hobbies", "interests", "languages", "references",
}


def preprocess_resume_text(raw_text: str) -> str:
    """
    Insert [SECTION: HEADER] markers before detected section headers.
    Preserves original wording; only adds markers so parsers can treat sections independently.
    """
    if not raw_text or not raw_text.strip():
        return raw_text
    lines = raw_text.splitlines()
    out = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            out.append(line)
            continue
        # Check if this line looks like a section header
        header = _detect_section_header(stripped)
        if header:
            out.append(f"[SECTION: {header}]")
        out.append(line)
    return "\n".join(out)


def _looks_like_person_name_or_title(line: str) -> bool:
    """Avoid treating 'SAURABH PANDEY' or 'FULL STACK DEVELOPER' as section headers."""
    stripped = line.strip()
    if not stripped or len(stripped) > 50:
        return False
    words = stripped.split()
    if not 2 <= len(words) <= 5:
        return False
    if not stripped.isupper() and not (stripped[0].isupper() if stripped else False):
        return False
    # All words alphabetic (or one allowed punctuation)
    for w in words:
        if len(w) <= 1 or len(w) > 20:
            return False
        if not all(c.isalpha() or c in ".-" for c in w):
            return False
    return True


def _detect_section_header(line: str) -> str | None:
    """
    Return section name for marker if line is a section header, else None.
    Do NOT treat person names or job titles (e.g. SAURABH PANDEY, FULL STACK DEVELOPER) as sections.
    """
    stripped = line.strip()
    lower = stripped.lower()
    if _looks_like_person_name_or_title(stripped):
        return None
    # Short ALL CAPS line that matches a known section
    if len(stripped) <= 45 and stripped.isupper() and len(stripped) >= 2:
        for known in SECTION_HEADERS:
            if lower == known or lower.startswith(known + " ") or known in lower:
                return stripped
        if re.match(r"^[A-Z][A-Z\s&\-/]+$", stripped) and len(stripped) <= 25:
            return stripped
    # Short line matching known headers (with or without colon)
    if len(stripped) <= 55:
        for known in SECTION_HEADERS:
            if lower == known or lower.startswith(known + ":") or lower.startswith(known + " "):
                return stripped if stripped.isupper() else known.upper().replace(" ", "_")
    return None
