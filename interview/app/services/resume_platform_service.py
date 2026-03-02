"""Resume platform service - extract email from resume, compute ATS score. Shortlist when ATS >= 85."""

import logging
import re
from typing import Optional

from app.services.resume_preprocess import preprocess_resume_text

logger = logging.getLogger(__name__)

# Strip [SECTION: ...] so it never appears in form fields
_SECTION_MARKER_RE = re.compile(r"\[SECTION:\s*[^\]]*\]\s*", re.IGNORECASE)


def _strip_section_marker(s: str) -> str:
    if not s or not isinstance(s, str):
        return s
    return _SECTION_MARKER_RE.sub("", s).strip()


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
    "python", "javascript", "java", "react", "next.js", "nextjs", "node", "node.js", "sql", "aws", "docker", "kubernetes",
    "html", "css", "typescript", "angular", "vue", "mongodb", "postgresql", "mysql", "redis",
    "git", "github", "rest", "api", "graphql", "machine learning", "tensorflow", "pytorch", "scikit-learn",
    "c++", "c#", ".net", "go", "golang", "rust", "php", "ruby", "ruby on rails", "rails", "django", "flask",
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


def _valid_link(u: str) -> bool:
    """Reject placeholder or incomplete links."""
    if not u or len(u) < 12:
        return False
    if u.rstrip("/").endswith("/_") or "/_ " in u:
        return False
    path_part = (u.split("/")[-1] or u).split("?")[0]
    if path_part.isupper() and len(path_part) <= 15:
        return False
    if path_part.lower() in ("linked", "example", "username", "url", "link", "xxx", "na", "tbd"):
        return False
    return True


def _categorize_links(urls: list[str]) -> dict[str, list[str]]:
    """Split flat URL list into platform buckets for form columns."""
    out: dict[str, list[str]] = {
        "links_github": [],
        "links_linkedin": [],
        "links_portfolio": [],
        "links_other": [],
    }
    lower_pats = [
        ("github.com", "links_github"),
        ("linkedin.com", "links_linkedin"),
        ("leetcode.com", "links_other"),
        ("geeksforgeeks.org", "links_other"),
        ("codechef.com", "links_other"),
        ("codeforces.com", "links_other"),
        ("hackerrank.com", "links_other"),
        ("portfolio", "links_portfolio"),
        ("personal site", "links_portfolio"),
        ("website", "links_portfolio"),
    ]
    for u in urls:
        if not u or not isinstance(u, str):
            continue
        lower = u.lower()
        assigned = False
        for pat, key in lower_pats:
            if pat in lower:
                out[key].append(u)
                assigned = True
                break
        if not assigned:
            # Portfolio-like: personal page, blog, etc.
            if any(x in lower for x in (".me", "dev.to", "medium.com", "blog.", "vercel.app", "netlify.app")):
                out["links_portfolio"].append(u)
            else:
                out["links_other"].append(u)
    return out


def _extract_links_from_links_section(text: str) -> list[str]:
    """
    Find LINKS/Links section and extract URLs. Handles format where platform name is on one line
    and URL or username is on the next (e.g. "GITHUB" then "https://github.com/user" or "username").
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out = []
    in_links = False
    stop_headers = ("details", "skills", "profile", "experience", "education", "projects", "certifications", "employment", "summary", "contact")
    i = 0
    while i < len(lines):
        line = lines[i]
        lower = line.lower()
        if not in_links:
            if lower in ("links", "link", "online presence", "profiles") or lower.startswith("links:") or lower.startswith("link:"):
                in_links = True
                i += 1
                continue
            i += 1
            continue
        if any(lower == h or lower.startswith(h + ":") for h in stop_headers) and len(line) < 40:
            break
        if re.match(r"^https?://", line, re.IGNORECASE):
            u = line.rstrip(".,;:)")
            if _valid_link(u):
                out.append(u)
        elif re.match(r"github\.com/", line, re.IGNORECASE) or re.match(r"linkedin\.com/", line, re.IGNORECASE):
            u = line if line.lower().startswith("http") else "https://" + line
            if _valid_link(u):
                out.append(u)
        elif lower in ("github", "git hub", "linkedin", "linked in", "leetcode", "portfolio", "website", "twitter", "medium", "gfg", "geeksforgeeks", "gfc", "codechef", "codeforces", "hackerrank"):
            next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if next_line.startswith("http") and _valid_link(next_line.rstrip(".,;:)")):
                out.append(next_line.rstrip(".,;:)"))
            elif next_line and not next_line.startswith("http") and " " not in next_line and len(next_line) < 50 and len(next_line) > 1:
                uname = next_line.rstrip(".,;:)").lstrip("/")
                if "github" in lower and uname:
                    out.append("https://github.com/" + uname)
                elif "linked" in lower and uname:
                    out.append("https://linkedin.com/in/" + uname)
                elif "leetcode" in lower and uname:
                    out.append("https://leetcode.com/" + uname)
                elif "gfg" in lower or "geeksforgeeks" in lower or "gfc" in lower:
                    out.append("https://geeksforgeeks.org/user/" + uname)
                elif "codechef" in lower and uname:
                    out.append("https://codechef.com/users/" + uname)
                elif "codeforces" in lower and uname:
                    out.append("https://codeforces.com/profile/" + uname)
                elif "hackerrank" in lower and uname:
                    out.append("https://hackerrank.com/" + uname)
            i += 1
        i += 1
    return out


def _extract_all_urls(text: str) -> list[str]:
    """Extract all URLs from text: full https?://, bare domains, label-style, and LINKS section."""
    seen = set()
    out = []

    # 0) LINKS section: platform on one line, URL/username on next (two-column resumes)
    for u in _extract_links_from_links_section(text):
        key = u.lower()
        if key not in seen and _valid_link(u):
            seen.add(key)
            out.append(u)

    # 1) Full URLs: http:// or https://
    for m in re.finditer(r"https?://[^\s<>\"')\]\]]+", text, re.IGNORECASE):
        u = m.group(0).rstrip(".,;:)\\]")
        if len(u) > 10 and len(u) < 500 and u not in seen and _valid_link(u):
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
        r"geeksforgeeks\.org/[a-zA-Z0-9_.-]+(?:\/[a-zA-Z0-9_.-]*)*",
        r"codechef\.com/users/[a-zA-Z0-9_-]+",
        r"codeforces\.com/profile/[a-zA-Z0-9_-]+",
        r"hackerrank\.com/[a-zA-Z0-9_-]+",
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
            if key not in seen and _valid_link(u):
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
            if not _valid_link(u):
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
        # Check if this line is a section header (allow up to 50 chars so "Key Projects" etc. match)
        if not in_section:
            for h in normalized_headers:
                is_short_line = len(stripped) <= 50
                if ln_lower == h or (is_short_line and (ln_lower.startswith(h + ":") or ln_lower.startswith(h + " "))):
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
    # Fallback: find header as substring anywhere (e.g. "Projects:" or "Project Experience")
    if not out:
        text_lower = text.lower()
        for header in section_headers:
            h = _normalize_header(header)
            idx = text_lower.find(h)
            if idx >= 0:
                start = idx + len(header) if len(header) > len(h) else idx + len(h)
                chunk = text[start : start + 1800]
                for ln in chunk.splitlines():
                    ln = ln.strip()
                    if ln and len(ln) > 2 and len(out) < max_lines:
                        ln_lower = ln.lower()
                        if any(ln_lower.startswith(s) for s in stop_headers) and len(ln) < 50:
                            break
                        out.append(ln)
                if out:
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
            "links": [], "links_github": [], "links_linkedin": [], "links_portfolio": [], "links_other": [],
            "projects": [], "certificates": [], "experience": [],
            "resume_text": "",
        }
    text = resume_text.strip()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    all_links = _extract_all_urls(text)
    result = {
        "email": extract_email_from_resume(text) or "",
        "full_name": "",
        "job_role": "",
        "tech_stack": [],
        "links": all_links,
        "projects": [],
        "certificates": [],
        "experience": [],
        "resume_text": text,
    }
    categorized = _categorize_links(result["links"])
    result["links_github"] = categorized["links_github"]
    result["links_linkedin"] = categorized["links_linkedin"]
    result["links_portfolio"] = categorized["links_portfolio"]
    result["links_other"] = categorized["links_other"]

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

    # Tech stack: from Skills/Technologies section (match "SKILLS" or "Skills:" with or without colon)
    text_lower = text.lower()
    skills_section = None
    # With colon
    for sep in ("skills:", "technical skills:", "technologies:", "tech stack:", "expertise:", "developer tools:", "technologies/frameworks", "technologies/frameworks :", "tools & technologies:"):
        idx = text_lower.find(sep)
        if idx >= 0:
            start = idx + len(sep)
            end = text_lower.find("\n\n", start)
            skills_section = text_lower[start : (end if end >= 0 else start + 800)]
            break
    # Without colon: "SKILLS" or "Skills" as whole line (two-column resumes often use this)
    if not skills_section:
        for pattern in (r"(?:^|\n)skills\s*\n", r"(?:^|\n)technical\s+skills\s*\n", r"(?:^|\n)tech\s+stack\s*\n"):
            m = re.search(pattern, text_lower)
            if m:
                start = m.end()
                end = text_lower.find("\n\n", start)
                chunk = text_lower[start : (end if end >= 0 else start + 800)]
                if len(chunk.strip()) > 3:
                    skills_section = chunk
                    break
    found = []
    if skills_section:
        for tech in sorted(TECH_SKILLS, key=len, reverse=True):
            if tech not in skills_section:
                continue
            if any(tech in f for f in found):
                continue
            found.append(tech)
        if not found:
            for line in skills_section.splitlines():
                line = line.strip()
                if not line or len(line) > 80:
                    continue
                if line in ("links", "details", "profile", "experience", "education", "projects"):
                    break
                found.append(line)
    if not found:
        for line in lines:
            line_lower = line.lower()
            if len(line_lower) > 200:
                continue
            matches = []
            for tech in sorted(TECH_SKILLS, key=len, reverse=True):
                if tech in line_lower and not any(tech in m for m in matches):
                    matches.append(tech)
            if len(matches) >= 2:
                found = matches[:15]
                break
    result["tech_stack"] = found[:20]

    # Projects (Project 1, Project 2, etc.) — many header variants
    result["projects"] = _extract_section_lines(
        text,
        (
            "projects:", "project:", "key projects:", "personal projects:",
            "selected projects:", "project experience:", "project details:",
            "projects &", "project work:", "projects and",
        ),
        max_lines=15,
    )

    # Certificates (and achievements, awards, courses)
    result["certificates"] = _extract_section_lines(
        text,
        (
            "certifications:", "certificate:", "certificates:", "achievements:",
            "achievement:", "certification ", "awards:", "courses:", "training:",
            "professional development:", "education & certifications:",
        ),
        max_lines=15,
    )

    # Experience (work experience lines)
    result["experience"] = _extract_section_lines(
        text,
        ("experience:", "work experience:", "employment:", "professional experience:", "work history:"),
        max_lines=15,
    )

    # Strip section markers from all outputs so they never leak into the form
    def _strip_list(items: list) -> list:
        return [_strip_section_marker(x) for x in items if _strip_section_marker(x)]

    result["full_name"] = _strip_section_marker(result.get("full_name") or "")
    result["job_role"] = _strip_section_marker(result.get("job_role") or "")
    result["email"] = _strip_section_marker(result.get("email") or "")
    result["links"] = _strip_list(result.get("links") or [])
    result["links_github"] = _strip_list(result.get("links_github") or [])
    result["links_linkedin"] = _strip_list(result.get("links_linkedin") or [])
    result["links_portfolio"] = _strip_list(result.get("links_portfolio") or [])
    result["links_other"] = _strip_list(result.get("links_other") or [])
    result["tech_stack"] = _strip_list(result.get("tech_stack") or [])
    result["projects"] = _strip_list(result.get("projects") or [])
    result["certificates"] = _strip_list(result.get("certificates") or [])
    result["experience"] = _strip_list(result.get("experience") or [])

    return result


async def extract_resume_details_async(resume_text: str) -> dict:
    """
    Extract structured details: preprocess with [SECTION: X] markers, then try LLM parse;
    on failure or missing API key, fall back to rule-based extraction on preprocessed text.
    """
    if not resume_text or not isinstance(resume_text, str):
        return {
            "email": "", "full_name": "", "job_role": "", "tech_stack": [],
            "links": [], "links_github": [], "links_linkedin": [], "links_portfolio": [], "links_other": [],
            "projects": [], "certificates": [], "experience": [],
            "resume_text": "",
        }
    original = resume_text.strip()
    preprocessed = preprocess_resume_text(original)
    try:
        from app.services.resume_llm_parser import parse_resume_with_llm
        llm_result = await parse_resume_with_llm(preprocessed, original)
        if llm_result:
            return llm_result
    except Exception as e:
        logger.debug("LLM resume parse skipped or failed: %s", e)
    return extract_resume_details(preprocessed)


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
