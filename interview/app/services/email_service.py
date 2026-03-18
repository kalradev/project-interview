"""Email service - send invite via Brevo or SMTP with professional HTML + plain text."""

import logging
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


def _format_interview_time_local(interview_scheduled_at: datetime | None) -> str:
    """Format interview time in the configured interview timezone (e.g. Asia/Kolkata) so the email shows the correct local time."""
    if not interview_scheduled_at:
        return "within 1–2 days (you will receive a reminder with exact time)"
    dt = interview_scheduled_at
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    settings = get_settings()
    tz_name = getattr(settings, "interview_timezone", "UTC") or "UTC"
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = timezone.utc
    local_dt = dt.astimezone(tz)
    # e.g. "08 March 2026 at 11:00 AM IST"
    time_str = local_dt.strftime("%d %B %Y at %I:%M %p")
    tz_abbr = local_dt.strftime("%Z")
    if tz_abbr and tz_abbr.strip():
        time_str = f"{time_str} {tz_abbr.strip()}"
    return time_str


def _interview_window_text() -> str:
    """Return human-readable interview window from config (e.g. '11:00 AM–5:00 PM')."""
    s = get_settings()
    start = getattr(s, "interview_window_start_hour", 11)
    end = getattr(s, "interview_window_end_hour", 17)

    def _hour_str(h: int) -> str:
        h12 = 12 if (h % 12) == 0 else (h % 12)
        period = "PM" if h >= 12 else "AM"
        return f"{h12}:00 {period}"

    return f"{_hour_str(start)}–{_hour_str(end)}"


# Brand colors for email (professional blue palette)
EMAIL_PRIMARY = "#0369a1"
EMAIL_PRIMARY_LIGHT = "#e0f2fe"
EMAIL_BORDER = "#e2e8f0"
EMAIL_TEXT = "#0f172a"
EMAIL_MUTED = "#64748b"
EMAIL_BG = "#f8fafc"


def _build_invite_plain(
    to_email: str,
    password: str,
    interview_scheduled_at: datetime | None,
    setup_download_url: str,
    candidate_name: str | None,
    interview_link_url: str | None = None,
) -> str:
    """Return plain-text body."""
    time_str = _format_interview_time_local(interview_scheduled_at)
    name = candidate_name or "Candidate"
    take_interview_block = ""
    if interview_link_url:
        take_interview_block = f"""
TAKE YOUR INTERVIEW (browser – no install)
Click this link to start your interview in your browser. You will be asked to stay in full screen; do not switch tabs.
{interview_link_url}

"""
    return f"""Hello {name},

You have been shortlisted for an interview. Please use the details below to take the interview.

LOGIN CREDENTIALS
• Email: {to_email}
• Password: {password}

INTERVIEW TIMING
{time_str}
(Interviews are scheduled between {_interview_window_text()}.)
{take_interview_block}SETUP (Interview Agent app – optional)
1. Download and install the Interview Agent from: {setup_download_url}
2. Open the app and use "Start in standalone mode" to practice, or enter the API URL and Session ID when provided by the recruiter.
3. On the day of the interview, log in with the email and password above. The screen will lock and the interview will begin.

Do not share your password. If you did not apply for this role, please ignore this email.

Best regards,
Interview Team
"""


def _build_invite_html(
    to_email: str,
    password: str,
    interview_scheduled_at: datetime | None,
    setup_download_url: str,
    candidate_name: str | None,
    interview_link_url: str | None = None,
) -> str:
    """Return professional HTML body (inline styles for email clients)."""
    time_str = _format_interview_time_local(interview_scheduled_at)
    name = candidate_name or "Candidate"
    take_interview_section = ""
    if interview_link_url:
        take_interview_section = f"""
          <tr>
            <td style="padding: 0 32px 20px;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background: linear-gradient(135deg, {EMAIL_PRIMARY} 0%, #0ea5e9 100%); border-radius: 10px; border: 1px solid {EMAIL_BORDER};">
                <tr>
                  <td style="padding: 20px 24px; text-align: center;">
                    <p style="margin: 0 0 12px; font-size: 12px; font-weight: 700; color: rgba(255,255,255,0.9); text-transform: uppercase; letter-spacing: 0.04em;">Take your interview (no install)</p>
                    <p style="margin: 0 0 16px; font-size: 15px; color: #fff;">Click the button below to start your interview in your browser. Stay in full screen and do not switch tabs.</p>
                    <a href="{interview_link_url}" style="display: inline-block; padding: 12px 24px; background: #fff; color: {EMAIL_PRIMARY}; font-weight: 700; font-size: 15px; text-decoration: none; border-radius: 8px;">Start interview</a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Interview – Login Details</title>
</head>
<body style="margin:0; padding:0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; font-size: 15px; line-height: 1.5; color: {EMAIL_TEXT}; background-color: #f1f5f9;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f1f5f9;">
    <tr>
      <td align="center" style="padding: 32px 16px;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 560px; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 24px rgba(12, 25, 41, 0.08); border: 1px solid {EMAIL_BORDER};">
          <!-- Header -->
          <tr>
            <td style="padding: 28px 32px 20px; border-bottom: 1px solid {EMAIL_BORDER};">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                <tr>
                  <td>
                    <div style="width: 44px; height: 44px; background: linear-gradient(135deg, {EMAIL_PRIMARY} 0%, #0ea5e9 100%); border-radius: 10px; display: inline-block; text-align: center; line-height: 44px; font-weight: 700; font-size: 18px; color: #ffffff; letter-spacing: -0.02em;">IA</div>
                    <span style="margin-left: 12px; font-size: 18px; font-weight: 700; color: {EMAIL_TEXT}; letter-spacing: -0.02em;">Interview Admin</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <!-- Greeting -->
          <tr>
            <td style="padding: 28px 32px 8px;">
              <p style="margin: 0 0 8px; font-size: 16px; color: {EMAIL_TEXT}; font-weight: 600;">Hello {name},</p>
              <p style="margin: 0; font-size: 15px; color: {EMAIL_MUTED}; line-height: 1.5;">You have been shortlisted for an interview. Use the details below to log in and complete your interview.</p>
            </td>
          </tr>
          <!-- Credentials box -->
          <tr>
            <td style="padding: 16px 32px;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: {EMAIL_BG}; border-radius: 10px; border: 1px solid {EMAIL_BORDER};">
                <tr>
                  <td style="padding: 20px 24px;">
                    <p style="margin: 0 0 12px; font-size: 12px; font-weight: 700; color: {EMAIL_MUTED}; text-transform: uppercase; letter-spacing: 0.04em;">Login credentials</p>
                    <p style="margin: 0 0 6px; font-size: 15px; color: {EMAIL_TEXT};"><strong>Email:</strong> <span style="color: {EMAIL_PRIMARY}; font-weight: 600;">{to_email}</span></p>
                    <p style="margin: 0; font-size: 15px; color: {EMAIL_TEXT};"><strong>Password:</strong> <code style="background: #e2e8f0; padding: 4px 8px; border-radius: 6px; font-size: 14px;">{password}</code></p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <!-- Interview timing -->
          <tr>
            <td style="padding: 0 32px 16px;">
              <p style="margin: 0 0 6px; font-size: 12px; font-weight: 700; color: {EMAIL_MUTED}; text-transform: uppercase; letter-spacing: 0.04em;">Interview timing</p>
              <p style="margin: 0; font-size: 15px; color: {EMAIL_TEXT}; font-weight: 500;">{time_str}</p>
              <p style="margin: 6px 0 0; font-size: 13px; color: {EMAIL_MUTED};">Interviews are scheduled between {_interview_window_text()}.</p>
            </td>
          </tr>
          <!-- Take interview link (browser) -->
          {take_interview_section}
          <!-- Setup steps -->
          <tr>
            <td style="padding: 0 32px 24px;">
              <p style="margin: 0 0 12px; font-size: 12px; font-weight: 700; color: {EMAIL_MUTED}; text-transform: uppercase; letter-spacing: 0.04em;">Setup (Interview Agent app)</p>
              <ol style="margin: 0; padding-left: 20px; color: {EMAIL_TEXT}; font-size: 15px; line-height: 1.7;">
                <li style="margin-bottom: 8px;">Download and install the <strong>Interview Agent</strong> from <a href="{setup_download_url}" style="color: {EMAIL_PRIMARY}; font-weight: 600; text-decoration: none;">this link</a>.</li>
                <li style="margin-bottom: 8px;">Open the app. Use <strong>Start in standalone mode</strong> to practice, or enter the API URL and Session ID when provided by the recruiter.</li>
                <li>On the day of the interview, log in with the email and password above. The screen will lock and the interview will begin.</li>
              </ol>
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="padding: 20px 32px 28px; border-top: 1px solid {EMAIL_BORDER}; background-color: {EMAIL_BG}; border-radius: 0 0 12px 12px;">
              <p style="margin: 0 0 8px; font-size: 13px; color: {EMAIL_MUTED}; line-height: 1.5;">Do not share your password. If you did not apply for this role, please ignore this email.</p>
              <p style="margin: 0; font-size: 14px; font-weight: 600; color: {EMAIL_TEXT};">Best regards,<br>Interview Team</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


def _build_invite_body(
    to_email: str,
    password: str,
    interview_scheduled_at: datetime | None,
    setup_download_url: str,
    candidate_name: str | None,
    interview_link_url: str | None = None,
) -> tuple[str, str, str]:
    """Return (subject, plain_text_body, html_body)."""
    subject = "Your Interview – Login Details & Setup"
    plain = _build_invite_plain(
        to_email, password, interview_scheduled_at, setup_download_url, candidate_name, interview_link_url
    )
    html = _build_invite_html(
        to_email, password, interview_scheduled_at, setup_download_url, candidate_name, interview_link_url
    )
    return subject, plain, html


def _send_via_brevo(
    to_email: str,
    subject: str,
    plain_body: str,
    html_body: str,
    from_email: str,
    api_key: str,
) -> tuple[bool, str]:
    """Send using Brevo (Sendinblue) v3 API. Returns (True, '') on success, (False, error_msg) on failure."""
    url = "https://api.brevo.com/v3/smtp/email"
    payload = {
        "sender": {"name": "Interview Team", "email": from_email},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": plain_body,
        "htmlContent": html_body,
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
    plain_body: str,
    html_body: str,
    from_email: str,
    host: str,
    port: int,
    user: str,
    password: str,
) -> tuple[bool, str]:
    """Send using SMTP with multipart (plain + HTML). Returns (True, '') on success, (False, error_msg) on failure."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))
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
    interview_link_url: str | None = None,
) -> tuple[bool, str]:
    """
    Send interview invite email with login credentials, interview time, setup link, and optional browser interview link.
    Sends both professional HTML and plain-text versions.
    Uses SMTP first if configured; else Brevo.
    Returns (True, '') if sent, (False, error_message) if not configured or send failed.
    """
    settings = get_settings()
    subject, plain_body, html_body = _build_invite_body(
        to_email, password, interview_scheduled_at, setup_download_url, candidate_name, interview_link_url
    )

    if settings.smtp_host and settings.smtp_user and settings.smtp_password:
        from_email = settings.smtp_from_email or settings.smtp_user
        ok, err = _send_via_smtp(
            to_email,
            subject,
            plain_body,
            html_body,
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
            to_email, subject, plain_body, html_body, from_email, settings.brevo_api_key
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
