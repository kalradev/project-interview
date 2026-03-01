"""Resume platform service - extract email from resume, compute ATS score. Shortlist when ATS >= 85."""

import re
from typing import Optional


# Job-title keywords: prefer lines containing these for job_role (avoid address/location)
JOB_ROLE_KEYWORDS = [
    "developer", "engineer", "analyst", "architect", "manager", "lead", "specialist",
    "consultant", "designer", "scientist", "administrator", "intern", "associate",
    "full stack", "frontend", "backend", "data ", "software", "web ", "mobile ",
    "devops", "cloud", "qa", "test ", "product ", "project ",
]
# Location/address hints: reject lines that look like address for job_role
LOCATION_HINTS = re.compile(
    r"\d{6}|^\d+\s|street|st\.|avenue|ave\.|rajasthan|maharashtra|delhi|bangalore|pincode|pin\s|,\s*\d{5}",
    re.I,
)

# Tech/skill keywords to detect from resume (lowercase)
TECH_SKILLS = [
    "python", "javascript", "java", "react", "node", "node.js", "sql", "aws", "docker", "kubernetes",
    "html", "css", "typescript", "angular", "vue", "mongodb", "postgresql", "mysql", "redis",
    "git", "rest", "api", "graphql", "machine learning", "tensorflow", "pytorch", "scikit-learn",
    "c++", "c#", ".net", "go", "golang", "rust", "php", "ruby", "rails", "django", "flask",
    "agile", "scrum", "jira", "ci/cd", "jenkins", "terraform", "ansible", "linux",
]

# Common keywords that boost ATS (adjust per job role if needed)
RESUME_KEYWORDS = [
    "experience", "skills", "education", "project", "certification",
    "python", "javascript", "react", "node", "sql", "api", "aws",
    "leadership", "team", "communication", "analytics", "development",
]


def extract_email_from_resume(resume_text: str) -> Optional[str]:
    """Extract first valid-looking email from resume text."""
    if not resume_text or not isinstance(resume_text, str):
        return None
    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    match = re.search(pattern, resume_text)
    return match.group(0).strip().lower() if match else None


def _extract_all_urls(text: str) -> list[str]:
    """Extract all URLs from text: full https?:// URLs and bare domains (github.com, linkedin.com, etc.)."""
    seen = set()
    out = []

    # 1) Full URLs: http:// or https://
    for m in re.finditer(r"https?://[^\s<>\"')\]\]]+", text, re.IGNORECASE):
        u = m.group(0).rstrip(".,;:)\\]")
        if len(u) > 10 and len(u) < 500 and u not in seen:
            seen.add(u)
            out.append(u)

    # 2) Bare domains common in resumes (add https://)
    bare_patterns = [
        r"github\.com/[a-zA-Z0-9_.-]+(?:\/[a-zA-Z0-9_.-]*)*",
        r"linkedin\.com/in/[a-zA-Z0-9_-]+",
        r"bitbucket\.org/[a-zA-Z0-9_.-]+(?:\/[a-zA-Z0-9_.-]*)*",
        r"gitlab\.com/[a-zA-Z0-9_.-]+(?:\/[a-zA-Z0-9_.-]*)*",
        r"stackoverflow\.com/users/[a-zA-Z0-9_-]+",
        r"leetcode\.com/[a-zA-Z0-9_-]+",
        r"medium\.com/@[a-zA-Z0-9_-]+",
        r"twitter\.com/[a-zA-Z0-9_]+",
        r"x\.com/[a-zA-Z0-9_]+",
    ]
    for pattern in bare_patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            raw = m.group(0).rstrip(".,;:)")
            if not raw or len(raw) < 10 or len(raw) > 400:
                continue
            u = raw if raw.lower().startswith("http") else "https://" + raw
            key = u.lower()
            if key not in seen:
                seen.add(key)
                out.append(u)

    # 3) "Normal words" labels: "GitHub: username", "LinkedIn: name", "Portfolio: url", etc.
    label_patterns = [
        (r"(?:github|git\s*hub)\s*[:\-]\s*([^\s,\n]+)", "https://github.com/{}"),
        (r"(?:linkedin|linked\s*in)\s*[:\-]\s*([^\s,\n]+)", "https://linkedin.com/in/{}"),
        (r"(?:portfolio|website|personal\s*site)\s*[:\-]\s*([^\s,\n]+)", None),
        (r"(?:blog|medium)\s*[:\-]\s*([^\s,\n]+)", None),
        (r"(?:twitter|x\.com)\s*[:\-]\s*([^\s,\n]+)", "https://twitter.com/{}"),
        (r"(?:leetcode|code)\s*[:\-]\s*([^\s,\n]+)", None),
    ]
    for pattern, template in label_patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            value = m.group(1).strip().rstrip(".,;:)")
            if not value or len(value) > 350:
                continue
            if value.lower().startswith("http"):
                u = value
            elif template and "/" not in value and " " not in value:
                u = template.format(value.lstrip("/"))
            elif "." in value and not value.lower().startswith("http"):
                u = value if value.lower().startswith("www.") else "https://" + value
            elif template is None:
                continue
            else:
                continue
            u = u.rstrip(".,;:)")
            if len(u) < 12:
                continue
            key = u.lower()
            if key not in seen:
                seen.add(key)
                out.append(u)

    return out[:30]


def _normalize_header(h: str) -> str:
    """Return header lowercase and without trailing colon for matching."""
    return h.lower().rstrip(":").strip()


def _extract_section_lines(text: str, section_headers: tuple[str, ...], max_lines: int = 15) -> list[str]:
    """Find a section by header (e.g. 'Projects', 'Experience') and return following non-empty lines.
    Matches line that starts with header (with or without colon), case-insensitive."""
    all_lines = text.splitlines()
    normalized_headers = [_normalize_header(h) for h in section_headers]
    stop_headers = ("education", "skills", "certification", "certificates", "projects", "project",
                    "experience", "work experience", "objective", "summary", "contact", "references",
                    "achievements", "technical", "languages", "hobbies", "interests")
    out = []
    in_section = False
    for i, line in enumerate(all_lines):
        stripped = line.strip()
        if not stripped:
            continue
        ln_lower = stripped.lower()
        # Check if this line is a section header (short line that starts with header)
        if not in_section:
            for h in normalized_headers:
                is_short_line = len(stripped) <= 35
                if ln_lower == h or (is_short_line and ln_lower.startswith(h + ":")) or (is_short_line and ln_lower.startswith(h + " ")):
                    in_section = True
                    # First line might be "Projects: Project 1" - take the part after colon if present
                    if ":" in stripped:
                        after_colon = stripped.split(":", 1)[1].strip()
                        if len(after_colon) > 2:
                            out.append(after_colon)
                    break
            continue
        # We're in section; stop at next section header
        if any(ln_lower.startswith(s) for s in stop_headers) and len(stripped) < 50:
            if not any(ln_lower.startswith(h) for h in normalized_headers):
                break
        if len(stripped) > 2:
            out.append(stripped)
        if len(out) >= max_lines:
            break
    # Fallback: find header as substring (e.g. "Projects:" in middle of line)
    if not out:
        text_lower = text.lower()
        for header in section_headers:
            h = header.lower()
            idx = text_lower.find(h)
            if idx >= 0:
                start = idx + len(header) if header.endswith(":") else idx + len(h)
                chunk = text[start : start + 1500]
                for ln in chunk.splitlines():
                    ln = ln.strip()
                    if ln and len(ln) > 2 and len(out) < max_lines:
                        ln_lower = ln.lower()
                        if any(ln_lower.startswith(s) for s in stop_headers) and len(ln) < 50:
                            break
                        out.append(ln)
                break
    return out[:max_lines]


def extract_resume_details(resume_text: str) -> dict:
    """
    Extract structured details from resume text for form pre-fill.
    Returns dict with keys: email, full_name, job_role, tech_stack, links, projects, certificates, experience, resume_text.
    """
    if not resume_text or not isinstance(resume_text, str):
        return {
            "email": "", "full_name": "", "job_role": "", "tech_stack": [],
            "links": [], "projects": [], "certificates": [], "experience": [],
            "resume_text": "",
        }
    text = resume_text.strip()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    result = {
        "email": extract_email_from_resume(text) or "",
        "full_name": "",
        "job_role": "",
        "tech_stack": [],
        "links": _extract_all_urls(text),
        "projects": [],
        "certificates": [],
        "experience": [],
        "resume_text": text,
    }

    # Full name: often first non-empty line (if it looks like a name: 2-4 words, no @)
    for line in lines[:5]:
        if "@" in line or re.search(r"\d{10}", line) or len(line) > 50:
            continue
        words = line.split()
        if 2 <= len(words) <= 4 and all(w[0].isupper() or not w.isalpha() for w in words if w):
            result["full_name"] = line
            break

    for line in lines[:15]:
        for prefix in ("name:", "full name:", "candidate:", "applicant:"):
            if line.lower().startswith(prefix):
                result["full_name"] = line[len(prefix):].strip()
                break

    # Job role: prefer lines that look like job titles (developer, analyst, etc.), skip address/location
    def _looks_like_role(line: str) -> bool:
        if not line or "@" in line or len(line) > 55:
            return False
        if LOCATION_HINTS.search(line):
            return False
        lower = line.lower()
        return any(k in lower for k in JOB_ROLE_KEYWORDS)

    for line in lines[:25]:
        lower = line.lower()
        for prefix in ("objective:", "applying for:", "role:", "position:", "title:", "target role:", "desired role:", "profile:", "summary:"):
            if lower.startswith(prefix):
                val = line[len(prefix):].strip()
                if val and not LOCATION_HINTS.search(val):
                    result["job_role"] = val
                    break
        if result["job_role"]:
            break

    if not result["job_role"]:
        for line in lines[1:15]:
            if _looks_like_role(line):
                result["job_role"] = line
                break
    if not result["job_role"]:
        for line in lines[1:10]:
            if 5 < len(line) < 55 and "@" not in line and not line[0].isdigit() and not LOCATION_HINTS.search(line):
                result["job_role"] = line
                break

    # Tech stack: only from Skills/Technologies section so we don't pick job-description text
    text_lower = text.lower()
    skills_section = None
    for sep in ("skills:", "technical skills:", "technologies:", "tech stack:", "expertise:", "developer tools:", "technologies/frameworks", "technologies/frameworks :"):
        idx = text_lower.find(sep)
        if idx >= 0:
            end = text_lower.find("\n\n", idx + len(sep))
            skills_section = (text_lower[idx + len(sep):end if end >= 0 else idx + 600])
            break
    # Only extract from skills section; if none found, leave tech_stack empty (no guessing from full text)
    found = []
    if skills_section:
        # Prefer longer matches first (e.g. "node.js" before "node") to avoid fragments
        for tech in sorted(TECH_SKILLS, key=len, reverse=True):
            if tech not in skills_section:
                continue
            if any(tech in f for f in found):
                continue
            found.append(tech)
    result["tech_stack"] = found[:15]

    # Projects (Project 1, Project 2, etc.)
    result["projects"] = _extract_section_lines(
        text,
        ("projects:", "project:", "key projects:", "personal projects:"),
        max_lines=12,
    )

    # Certificates (and achievements that often list certifications)
    result["certificates"] = _extract_section_lines(
        text,
        ("certifications:", "certificate:", "certificates:", "achievements:", "achievement:", "certification "),
        max_lines=15,
    )

    # Experience (work experience lines)
    result["experience"] = _extract_section_lines(
        text,
        ("experience:", "work experience:", "employment:", "professional experience:", "work history:"),
        max_lines=15,
    )

    return result


def compute_ats_score(resume_text: str, job_role: str = "") -> float:
    """
    Compute a simple ATS-style score from resume text (0-100).
    Uses keyword presence and length heuristics. Replace with real ATS/LLM in production.
    """
    if not resume_text or not isinstance(resume_text, str):
        return 0.0
    text_lower = resume_text.lower()
    role_lower = job_role.lower()
    score = 40.0  # base

    # Length (resume typically 200-1500 words)
    words = len(text_lower.split())
    if words >= 150:
        score += 15
    elif words >= 80:
        score += 10
    elif words >= 40:
        score += 5

    # Keyword matches
    keyword_hits = sum(1 for k in RESUME_KEYWORDS if k in text_lower)
    score += min(keyword_hits * 3, 25)

    # Job role mentioned in resume
    if role_lower and role_lower in text_lower:
        score += 10

    # Has email (completeness)
    if extract_email_from_resume(resume_text):
        score += 5

    return min(100.0, round(score, 1))


ATS_SHORTLIST_THRESHOLD = 85.0


def is_shortlisted(ats_score: float) -> bool:
    """Agent shortlists when ATS score is >= 85."""
    return ats_score >= ATS_SHORTLIST_THRESHOLD
