# AI Interview Integrity Agent

Production-ready interview monitoring agent that detects AI-assisted cheating. Built with **FastAPI** and **PostgreSQL**.

## Features

- **Session management**: Start/end interview sessions, unique session IDs
- **Event monitoring**: Tab switch, paste, copy, DevTools, idle, burst typing, instant large input
- **Typing analysis**: Keystroke timestamps → words/sec, burst detection, copy-paste detection
- **AI text detection**: Features (sentence length, vocabulary richness, perplexity, burstiness) + optional pre-trained classifier → `ai_probability` (0–1)
- **Integrity engine**: Base 100, weighted penalties → score 0–100, risk Low/Medium/High
- **REST + WebSocket**: Real-time event logging and live integrity score
- **OpenAI interview agent**: Generate interview questions by job role; multi-turn Q&A
- **JWT + RBAC**: Admin, Interviewer, Candidate

## Project structure

```
app/
  config.py           # Settings (Pydantic)
  main.py             # FastAPI app, lifespan, routes
  database/           # Async engine, session, Base
  models/             # User, InterviewSession, SuspiciousEvent, AnswerAnalysis, IntegrityScore
  schemas/            # Pydantic request/response
  auth/               # JWT, require_roles
  services/           # Session, Event, Integrity, AnswerAnalysis
  ml/                 # ai_text_detector, integrity_engine, typing_analysis
  routes/             # auth, sessions, events, integrity, websocket_router
scripts/
  seed_admin.py       # Create admin user
```

## Quick start

**Recommended: use a virtual environment** (avoids "file in use" errors with global uvicorn on Windows)

```powershell
# From the interview/ folder (Windows PowerShell)
.\setup_venv.ps1
.\run_server.ps1
```

Or manually:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Without venv** (requires PostgreSQL and no other process using uvicorn):

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Seed admin (optional): `python -m scripts.seed_admin`

API: http://localhost:8000 — Docs: http://localhost:8000/docs

### Troubleshooting

- **"The process cannot access the file... uvicorn.exe"** — Another process is using uvicorn. Use the venv method above (`.venv` has its own uvicorn), or close any terminal running `uvicorn app.main:app --reload` and retry.
- **"Ignoring invalid distribution -vicorn"** — Corrupted leftover in global site-packages. Either use the venv (then it’s ignored and harmless), or from `interview/` run: `python scripts/fix_invalid_uvicorn.py` (with no uvicorn running) to remove it.

## Environment

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | JWT signing key |
| `POSTGRES_HOST`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | PostgreSQL |
| `OPENAI_API_KEY` | OpenAI API key for the interview agent (required for AI questions) |
| `OPENAI_MODEL` | Optional; default `gpt-4o-mini` |
| **Email – Brevo (testing)** | |
| `BREVO_API_KEY` | Brevo API key; if set, invite emails use Brevo transactional API |
| `BREVO_FROM_EMAIL` | From address (verify sender in Brevo if needed) |
| **Email – SMTP (later)** | |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL` | When Brevo is not set, invite emails use SMTP |
| `AI_CLASSIFIER_PATH` | Path to `ai_classifier.pkl` (optional) |

**If invite emails are not received:**  
- **Brevo:** In [Brevo → Senders](https://app.brevo.com/senders/list), verify the address in `BREVO_FROM_EMAIL` (e.g. deevanshu30@gmail.com). Unverified senders are often blocked.  
- **Gmail SMTP:** Set `SMTP_PASSWORD` to a [Gmail App Password](https://support.google.com/accounts/answer/185833) (not your normal password).  
- When adding a candidate, the API now returns `email_sent` and `email_error`; the script and dashboard show the failure reason if the send fails.

## API overview

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/login` | Login (JSON: email, password) → JWT |
| POST | `/api/v1/auth/register` | Register user (Admin only) |
| POST | `/api/v1/sessions` | Start session |
| GET | `/api/v1/sessions/{id}` | Get session |
| POST | `/api/v1/sessions/end` | End session |
| POST | `/api/v1/events/log` | Log suspicious event |
| POST | `/api/v1/events/typing` | Submit keystrokes (analysis) |
| POST | `/api/v1/events/analyze-answer` | Analyze answer (AI + typing) |
| POST | `/api/v1/integrity/compute/{session_id}` | Compute integrity score |
| GET | `/api/v1/integrity/live/{session_id}` | Latest integrity score (PostgreSQL) |
| GET | `/api/v1/interview/status` | Check if OpenAI is configured |
| POST | `/api/v1/interview/next-question` | Get next AI question (job_role, previous_exchanges) |
| WS | `/api/v1/ws/events?session_id=...` | Real-time event log |
| WS | `/api/v1/ws/integrity?session_id=...` | Live integrity updates |

## Integrity score

- **Base**: 100  
- **Penalties**: `tab_switch × 10`, `paste × 15`, `ai_probability × 40`, `webcam_anomaly × 20`, others configurable  
- **Score**: max(0, 100 − total_penalty)  
- **Risk**: 80–100 Low, 50–79 Medium, &lt;50 High  

## ML classifier

Place a trained `ai_classifier.pkl` at `app/ml/ai_classifier.pkl` (or set `AI_CLASSIFIER_PATH`). It should be a joblib dump containing `classifier` (and optionally `vectorizer`). Without it, the detector uses a heuristic based on sentence length, burstiness, and vocabulary richness.
