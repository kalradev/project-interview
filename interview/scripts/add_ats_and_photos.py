"""
Add ats_score column to candidate_profiles and create session_photos table if missing.
Run from interview/ folder: python scripts/add_ats_and_photos.py
Uses sync engine; safe to run multiple times.
"""

import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from sqlalchemy import text
from app.config import get_settings
from app.database.base import Base
from app import models  # noqa: F401
from sqlalchemy import create_engine


def main():
    settings = get_settings()
    engine = create_engine(settings.database_url_sync)
    with engine.begin() as conn:
        # Add ats_score if not exists (PostgreSQL)
        conn.execute(text("""
            ALTER TABLE candidate_profiles
            ADD COLUMN IF NOT EXISTS ats_score DOUBLE PRECISION
        """))
        conn.execute(text("""
            ALTER TABLE candidate_profiles
            ADD COLUMN IF NOT EXISTS ats_details JSONB
        """))
        print("Added candidate_profiles.ats_score and ats_details if missing.")

        # Create session_photos and video_url on interview_sessions if missing
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS session_photos (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id UUID NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
                photo_url VARCHAR(512) NOT NULL,
                captured_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            ALTER TABLE interview_sessions
            ADD COLUMN IF NOT EXISTS video_url VARCHAR(512)
        """))
        conn.execute(text("""
            ALTER TABLE interview_sessions
            ADD COLUMN IF NOT EXISTS agent_report JSONB
        """))
        conn.execute(text("""
            ALTER TABLE interview_sessions
            ADD COLUMN IF NOT EXISTS face_lip_status VARCHAR(32)
        """))
        conn.execute(text("""
            ALTER TABLE interview_exchanges
            ADD COLUMN IF NOT EXISTS answered_quickly BOOLEAN DEFAULT FALSE
        """))
        conn.execute(text("""
            ALTER TABLE session_photos
            ADD COLUMN IF NOT EXISTS face_detected BOOLEAN DEFAULT TRUE
        """))
        for col in ("links", "projects", "certificates", "experience"):
            conn.execute(text(f"""
                ALTER TABLE candidate_profiles
                ADD COLUMN IF NOT EXISTS {col} JSONB
            """))
        print("Created session_photos, video_url, agent_report, face_lip_status, answered_quickly, face_detected, links, projects, certificates, experience if missing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
