# Interview Admin Dashboard

Web dashboard for admins to view **resumes (candidates)** and add new ones. When adding a resume, a toggle lets you decide whether to **send an invite and schedule an interview** for that candidate.

## Features

- **Login** with admin (or interviewer) credentials from the interview backend.
- **List candidates** – all resumes/candidates from the platform with status filter.
- **Add resume** – form to add a candidate (email, name, job role, tech stack, resume text/URL).
- **Toggle: Send invite & schedule interview** – when ON, the backend sends the invite email with credentials and setup link; when OFF, the candidate is added but no email is sent (for testing or manual follow-up).
- **Report** – view interview Q&A and integrity score per candidate.
- **Actions** – Next round, Select, Reject.

## Setup

1. **Backend** must be running (see `interview/README.md`):
   ```powershell
   cd interview
   .\run_server.ps1
   ```
   API at http://localhost:8000

2. **Create an admin user** if needed:
   ```powershell
   cd interview
   .\.venv\Scripts\Activate.ps1
   python -m scripts.seed_admin
   ```

3. **Install and run the dashboard**:
   ```powershell
   cd admin-dashboard
   npm install
   npm run dev
   ```
   Opens at http://localhost:3000. The dev server proxies `/api` to the backend.

4. **Optional** – if the backend is on another host/port, create `.env`:
   ```
   VITE_API_URL=http://localhost:8000
   ```
   Then restart `npm run dev`.

## Usage

1. Open http://localhost:3000 and sign in with admin email and password.
2. Click **"+ Add resume"** to open the form.
3. Fill in email, name, job role; optionally tech stack, resume text, resume URL.
4. Use the toggle **"Send invite & schedule interview"**:
   - **ON** – candidate is added and receives the invite email (credentials + setup link).
   - **OFF** – candidate is added only; no email is sent (useful for testing).
5. Click **Add candidate**. The list refreshes; new candidates appear in the table.
6. Use **Report** to see interview Q&A and integrity; use **Next round / Select / Reject** as needed.
