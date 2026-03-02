"""Send an invite email to a candidate by adding them via the API.
   Usage (from interview folder):
     python scripts/send_invite_to.py ahimank@2004gmail.com
   Or: python -m scripts.send_invite_to ahimank@2004gmail.com

   Requires the API to be running (uvicorn). Uses admin@example.com / admin123 by default.
   Set ADMIN_EMAIL, ADMIN_PASSWORD, API_BASE via env if needed."""

import json
import os
import sys
import urllib.request

# Defaults; override with env
API_BASE = os.environ.get("API_BASE", "http://localhost:8000")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")


def post(url, data, token=None):
    body = json.dumps(data).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.getcode(), json.loads(r.read().decode())


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/send_invite_to.py <email> [full_name] [job_role]")
        print("Example: python scripts/send_invite_to.py ahimank@2004gmail.com")
        sys.exit(1)

    email = sys.argv[1].strip()
    full_name = sys.argv[2].strip() if len(sys.argv) > 2 else "Candidate"
    job_role = sys.argv[3].strip() if len(sys.argv) > 3 else "Software Engineer"
    base = API_BASE.rstrip("/")

    # Login as admin
    try:
        code, data = post(
            f"{base}/api/v1/auth/login",
            {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
    except urllib.error.HTTPError as e:
        print(f"Login failed: {e.code} {e.read().decode()}")
        sys.exit(1)
    except Exception as e:
        print(f"Login error: {e}")
        sys.exit(1)

    if code != 200:
        print(f"Login failed: {code} {data}")
        sys.exit(1)
    token = data.get("access_token")
    if not token:
        print("Login response missing access_token")
        sys.exit(1)

    # Add candidate (sends invite email with password)
    try:
        code, data = post(
            f"{base}/api/v1/admin/candidates",
            {
                "email": email,
                "full_name": full_name,
                "job_role": job_role,
                "send_email": True,
            },
            token=token,
        )
    except urllib.error.HTTPError as e:
        print(f"Add candidate failed: {e.code} {e.read().decode()}")
        sys.exit(1)
    except Exception as e:
        print(f"Add candidate error: {e}")
        sys.exit(1)

    if code != 200:
        print(f"Add candidate failed: {code} {data}")
        sys.exit(1)

    email_sent = data.get("email_sent", False)
    email_error = data.get("email_error") or ""
    if email_sent:
        print(f"Invite email sent to {email}. They will receive login credentials and password.")
    else:
        print(f"Candidate added, but invite email was NOT sent to {email}.")
        if email_error:
            print(f"Reason: {email_error}")
        else:
            print("Check .env: set BREVO_API_KEY and BREVO_FROM_EMAIL (and verify sender in Brevo), or SMTP_* for Gmail.")
    print("Done.")


if __name__ == "__main__":
    main()
