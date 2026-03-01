"""
Test Brevo (invite) email. Run from the interview/ folder:

    python scripts/test_email.py your@email.com

Sends one invite email to the given address. Checks BREVO_API_KEY and BREVO_FROM_EMAIL from .env.
"""

import sys
from datetime import datetime, timezone, timedelta

# Run from interview/ so app is on path
sys.path.insert(0, ".")

from app.config import get_settings
from app.services.email_service import send_invite_email


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_email.py <to_email>")
        print("Example: python scripts/test_email.py you@example.com")
        sys.exit(1)

    to_email = sys.argv[1].strip()
    settings = get_settings()

    if not settings.brevo_api_key:
        print("ERROR: BREVO_API_KEY is not set in .env")
        sys.exit(1)
    if not settings.brevo_from_email:
        print("ERROR: BREVO_FROM_EMAIL is not set in .env")
        sys.exit(1)

    print(f"Sending test invite to: {to_email}")
    print(f"From: {settings.brevo_from_email}")
    scheduled = datetime.now(timezone.utc) + timedelta(days=1)
    ok = send_invite_email(
        to_email=to_email,
        password="TestPassword123!",
        interview_scheduled_at=scheduled,
        setup_download_url=settings.setup_app_download_url,
        candidate_name="Test Candidate",
    )
    if ok:
        print("OK: Email sent. Check inbox (and spam).")
    else:
        print("FAIL: Email was not sent. Fetching Brevo response for debugging...")
        import httpx
        url = "https://api.brevo.com/v3/smtp/email"
        payload = {
            "sender": {"name": "Interview Team", "email": settings.brevo_from_email},
            "to": [{"email": to_email}],
            "subject": "Test",
            "textContent": "Test body",
        }
        try:
            r = httpx.post(
                url,
                json=payload,
                headers={"api-key": settings.brevo_api_key, "Content-Type": "application/json"},
                timeout=15.0,
            )
            print(f"  Status: {r.status_code}")
            print(f"  Response: {r.text[:500]}")
        except Exception as e:
            print(f"  Error: {e}")


if __name__ == "__main__":
    main()
