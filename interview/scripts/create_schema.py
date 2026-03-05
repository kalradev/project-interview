"""
Create all tables (schema) in the PostgreSQL database.
Run from the interview/ folder so .env is loaded:

  python scripts/create_schema.py

or:

  python -m scripts.create_schema

Database config: uses DATABASE_URL or POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER,
POSTGRES_PASSWORD, POSTGRES_DB from environment (no hardcoded localhost).
Works with cloud PostgreSQL (Render, Supabase, etc.) when those env vars are set on deployment.

Tables created: users, candidate_profiles, interview_sessions, suspicious_events,
interview_exchanges, answer_analyses, integrity_scores, session_photos.
"""

import asyncio
import sys
from pathlib import Path

# Ensure interview/app is on path when run as script
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from app.config import get_settings
from app.database.base import Base
from app import models  # noqa: F401 - register all models with Base.metadata
from sqlalchemy import create_engine


def main():
    settings = get_settings()
    url = settings.database_url_sync
    print(f"Connecting to database: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")
    engine = create_engine(url)
    Base.metadata.create_all(bind=engine)
    print("Schema created successfully. Tables:")
    for t in sorted(Base.metadata.tables.keys()):
        print(f"  - {t}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
