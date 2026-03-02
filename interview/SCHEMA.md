# PostgreSQL schema – all tables

The app uses the database name from `.env`: **`POSTGRES_DB`** (e.g. `interview_integrity` or `interview-platform`).  
Tables are created automatically on startup via `init_db()` (SQLAlchemy `create_all`).

---

## 1. `users`

Stores all user accounts (admin, interviewer, candidate). Candidates are created when you import from admin.

| Column            | Type           | Nullable | Description                    |
|-------------------|----------------|----------|--------------------------------|
| id                | UUID           | NO (PK)  | Primary key                    |
| email             | VARCHAR(255)   | NO       | Unique, indexed                |
| hashed_password   | VARCHAR(255)   | NO       | Bcrypt hash                    |
| full_name         | VARCHAR(255)   | YES      | Display name                   |
| role              | Enum           | NO       | `admin`, `interviewer`, `candidate` |
| is_active         | BOOLEAN        | NO       | Default true                   |
| created_at        | TIMESTAMPTZ    | NO       |                                |
| updated_at        | TIMESTAMPTZ    | NO       |                                |

---

## 2. `candidate_profiles`

One row per candidate (from Naukri/manual import). Links to `users` via `user_id`.

| Column                  | Type           | Nullable | Description                    |
|-------------------------|----------------|----------|--------------------------------|
| id                      | UUID           | NO (PK)  | Primary key                    |
| user_id                 | UUID           | NO (FK→users) | Unique, one profile per user |
| job_role                | VARCHAR(255)   | NO       | e.g. "Software Engineer"       |
| tech_stack              | JSONB          | YES      | e.g. ["Python", "React"]      |
| source                  | VARCHAR(64)    | NO       | `manual`, `naukri`, `csv`, `platform` |
| ats_score               | DOUBLE PRECISION | YES    | ATS score from platform; shortlist if ≥ 85 |
| resume_text             | TEXT           | YES      | Raw resume text                |
| resume_url              | VARCHAR(512)   | YES      | Link to resume file            |
| interview_scheduled_at  | TIMESTAMPTZ    | YES      | When interview is scheduled     |
| status                  | VARCHAR(32)    | NO       | invited, scheduled, in_progress, completed, next_round, selected, rejected |
| invited_at              | TIMESTAMPTZ    | YES      | When invite email was sent     |
| photo_url               | VARCHAR(512)   | YES      | Path/URL of captured photo      |
| created_at              | TIMESTAMPTZ    | NO       |                                |
| updated_at              | TIMESTAMPTZ    | NO       |                                |

---

## 3. `interview_sessions`

One row per interview session. Candidate gets a session when they call “get or create session”.

| Column             | Type           | Nullable | Description                    |
|--------------------|----------------|----------|--------------------------------|
| id                 | UUID           | NO (PK)  | Primary key                    |
| session_token      | VARCHAR(64)    | NO       | Unique, indexed                |
| candidate_id       | UUID           | YES (FK→users) | Candidate user id          |
| interviewer_id     | UUID           | YES (FK→users) | Interviewer user id        |
| started_at         | TIMESTAMPTZ    | NO       |                                |
| ended_at           | TIMESTAMPTZ    | YES      | Set when session ends          |
| metadata           | JSONB          | YES      | e.g. job_role, tech_stack      |
| status             | VARCHAR(32)    | NO       | `active`, `ended`              |
| interview_summary  | TEXT           | YES      | Summary text when interview done |
| video_url          | VARCHAR(512)   | YES      | Recorded interview video path   |

---

## 3b. `session_photos`

Photos captured during the interview (for identity match after joining).

| Column       | Type           | Nullable | Description                    |
|--------------|----------------|----------|--------------------------------|
| id           | UUID           | NO (PK)  | Primary key                    |
| session_id   | UUID           | NO (FK→interview_sessions) | |
| photo_url    | VARCHAR(512)   | NO       | Path to uploaded photo         |
| captured_at  | TIMESTAMPTZ    | NO       |                                |

---

## 4. `suspicious_events`

Tab switch, paste, copy, etc. – one row per event.

| Column      | Type           | Nullable | Description                    |
|-------------|----------------|----------|--------------------------------|
| id          | UUID           | NO (PK)  | Primary key                    |
| session_id  | UUID           | NO (FK→interview_sessions) | |
| event_type  | Enum           | NO       | tab_switch, paste_event, copy_event, devtools_detection, idle_time, burst_typing, instant_large_input, webcam_anomaly |
| occurred_at | TIMESTAMPTZ    | NO       |                                |
| payload     | JSONB          | YES      | Extra data                     |
| severity    | VARCHAR(16)    | YES      | e.g. medium, high              |

---

## 5. `interview_exchanges`

One row per question–answer in the interview (for admin report).

| Column         | Type           | Nullable | Description                    |
|----------------|----------------|----------|--------------------------------|
| id             | UUID           | NO (PK)  | Primary key                    |
| session_id     | UUID           | NO (FK→interview_sessions) | |
| question_index | INTEGER        | NO       | 0-based order                  |
| question_text  | TEXT           | NO       |                                |
| answer_text    | TEXT           | NO       |                                |
| created_at     | TIMESTAMPTZ    | NO       |                                |

---

## 6. `answer_analyses`

Typing and AI-detection analysis per answer (from `/events/analyze-answer`).

| Column           | Type           | Nullable | Description                    |
|------------------|----------------|----------|--------------------------------|
| id               | UUID           | NO (PK)  | Primary key                    |
| session_id       | UUID           | NO (FK→interview_sessions) | |
| question_id       | VARCHAR(64)    | YES      |                                |
| answer_text      | TEXT           | YES      |                                |
| words_per_second | FLOAT          | YES      |                                |
| ai_probability   | FLOAT          | YES      | 0–1                            |
| features         | JSONB          | YES      | Detector features              |
| created_at       | TIMESTAMPTZ    | NO       |                                |

---

## 7. `integrity_scores`

Computed integrity score per session (from `/integrity/compute/{session_id}`).

| Column       | Type           | Nullable | Description                    |
|--------------|----------------|----------|--------------------------------|
| id           | UUID           | NO (PK)  | Primary key                    |
| session_id   | UUID           | NO (FK→interview_sessions) | |
| score        | FLOAT          | NO       | 0–100                          |
| risk_level   | VARCHAR(16)    | NO       | Low, Medium, High              |
| penalties    | JSONB          | YES      | Breakdown of penalties         |
| computed_at  | TIMESTAMPTZ    | NO       |                                |

---

## Relationships (for pgAdmin / ER view)

- **users** ← `candidate_profiles.user_id` (one profile per candidate user)
- **users** ← `interview_sessions.candidate_id`, `interview_sessions.interviewer_id`
- **interview_sessions** ← `suspicious_events.session_id`
- **interview_sessions** ← `interview_exchanges.session_id`
- **interview_sessions** ← `answer_analyses.session_id`
- **interview_sessions** ← `integrity_scores.session_id`

---

## How to check in pgAdmin

1. Connect to your PostgreSQL server.
2. Open the database named in your `.env`: **`POSTGRES_DB`** (e.g. `interview_integrity` or `interview-platform`).
3. Expand **Schemas → public → Tables**.
4. You should see:  
   `users`, `candidate_profiles`, `interview_sessions`, `suspicious_events`, `interview_exchanges`, `answer_analyses`, `integrity_scores`.

If any table is missing:

- Ensure the backend has run at least once (`.\run_server.ps1`) so `init_db()` has executed.
- Check that `POSTGRES_*` in `.env` point to the same database you’re viewing in pgAdmin.

To list tables in SQL:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_type = 'BASE TABLE'
ORDER BY table_name;
```

To describe a table (e.g. `users`):

```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'users'
ORDER BY ordinal_position;
```

Replace `users` with any table name to check its columns.
