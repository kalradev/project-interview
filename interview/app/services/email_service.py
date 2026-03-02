"""Email service - send invite via Brevo (testing) or SMTP (later)."""

import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


def _build_invite_body(
    to_email: str,
    password: str,
    interview_scheduled_at: datetime | None,
    setup_download_url: str,
    candidate_name: str | None,
) -> tuple[str, str]:
    """Return (subject, plain_text_body)."""
    time_str = (
        interview_scheduled_at.strftime("%d %B %Y at %I:%M %p")
        if interview_scheduled_at
        else "within 1–2 days (you will receive a reminder with exact time)"
    )
    name = candidate_name or "Candidate"
    subject = "Your Interview – Login Details & Setup"
    body = f"""
Hello {name},

You have been shortlisted for an interview. Please use the details below to take the interview.

**Login credentials**
• Email: {to_email}
• Password: {password}

**Interview timing**
{time_str}

**Setup (Interview Agent app)**
1. Download and install the Interview Agent from: {setup_download_url}
2. Open the app and click "Start in standalone mode" if you only need to practice, or enter the below when prompted:
   - API URL: (provided by the recruiter)
   - Session ID: (provided after you log in)
   - Use the same email and password above to log in on the interview portal if required.
3. On the day of the interview, log in with the email and password above. The screen will lock and the interview will begin.

Do not share your password. If you did not apply for this role, please ignore this email.

Best regards,
Interview Team
"""
    return subject, body.strip()


def _send_via_brevo(
    to_email: str,
    subject: str,
    body: str,
    from_email: str,
    api_key: str,
) -> tuple[bool, str]:
    """Send using Brevo (Sendinblue) v3 transactional API. Returns (True, '') on success, (False, error_msg) on failure."""
    url = "https://api.brevo.com/v3/smtp/email"
    payload = {
        "sender": {"name": "Interview Team", "email": from_email},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": body,
        "replyTo": {"email": from_email, "name": "Interview Team"},
    }
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.post(
                url,
                json=payload,
                headers={
                    "api-key": api_key,
                    "Content-Type": "application/json",
                },
            )
            if r.status_code != 201:
                err = f"Brevo returned {r.status_code}: {r.text[:300] if r.text else 'no body'}"
                logger.warning("Brevo invite email failed: %s", err)
                return False, err
            logger.info("Brevo invite email sent to %s", to_email)
            return True, ""
    except Exception as e:
        err = str(e)
        logger.warning("Brevo invite email exception: %s", e, exc_info=True)
        return False, err


def _send_via_smtp(
    to_email: str,
    subject: str,
    body: str,
    from_email: str,
    host: str,
    port: int,
    user: str,
    password: str,
) -> tuple[bool, str]:
    """Send using SMTP. Returns (True, '') on success, (False, error_msg) on failure."""
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    msg.attach(MIMEText(body, "plain"))
    try:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
        logger.info("SMTP invite email sent to %s", to_email)
        return True, ""
    except Exception as e:
        err = str(e)
        logger.warning("SMTP invite email exception: %s", e, exc_info=True)
        return False, err


def send_invite_email(
    to_email: str,
    password: str,
    interview_scheduled_at: datetime | None,
    setup_download_url: str,
    candidate_name: str | None = None,
) -> tuple[bool, str]:
    """
    Send interview invite email with login credentials, interview time, and setup link.
    Uses SMTP first if configured (e.g. Gmail) so From shows your address; else Brevo.
    Returns (True, '') if sent, (False, error_message) if not configured or send failed.
    """
    settings = get_settings()
    subject, body = _build_invite_body(
        to_email, password, interview_scheduled_at, setup_download_url, candidate_name
    )

    # Prefer SMTP when set: sent by your mail server, so From is your email (no Brevo relay).
    if settings.smtp_host and settings.smtp_user and settings.smtp_password:
        from_email = settings.smtp_from_email or settings.smtp_user
        ok, err = _send_via_smtp(
            to_email,
            subject,
            body,
            from_email,
            settings.smtp_host,
            settings.smtp_port,
            settings.smtp_user,
            settings.smtp_password,
        )
        return (ok, err) if ok else (False, f"SMTP: {err}")

    if settings.brevo_api_key:
        from_email = settings.brevo_from_email or settings.smtp_from_email or "noreply@example.com"
        ok, err = _send_via_brevo(
            to_email, subject, body, from_email, settings.brevo_api_key
        )
        if ok:
            return True, ""
        return False, f"Brevo: {err}"

    msg = (
        "No SMTP or Brevo configured. Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD for Gmail, "
        "or BREVO_API_KEY and BREVO_FROM_EMAIL in .env. For Brevo, verify the sender in Brevo dashboard."
    )
    logger.warning("Invite email not sent: %s", msg)
    return False, msg
