"""Async database connection and session management."""

import asyncio
import logging
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.database.base import Base

logger = logging.getLogger(__name__)

# Import models so they are registered with Base.metadata
from app import models  # noqa: F401

settings = get_settings()
# asyncpg doesn't accept sslmode in URL; enable SSL via connect_args for cloud DBs (Render, Supabase, etc.)
_url_raw = (settings.database_url_env or "") + (settings.database_url or "")
_cloud_ssl = any(
    h in _url_raw
    for h in ("render.com", "dpg-", "supabase", "railway", "neon.tech", "amazonaws.com")
)
async_engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args={"ssl": True} if _cloud_ssl else {},
)
async_session_factory = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create enum types and tables if they do not exist. For production use Alembic migrations."""
    try:
        # Add timeout to prevent hanging (30 seconds)
        await asyncio.wait_for(_init_db_internal(), timeout=30.0)
    except asyncio.TimeoutError:
        logger.error("Database initialization timed out after 30 seconds. Check database connection.")
        raise
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


async def _init_db_internal() -> None:
    """Internal function to create enum types and tables."""
    async with async_engine.begin() as conn:
        # Create PostgreSQL enum types first (required before tables that use them)
        await conn.execute(
            text("""
            DO $$ BEGIN
                CREATE TYPE public.userrole AS ENUM ('ADMIN', 'INTERVIEWER', 'CANDIDATE');
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """)
        )
        await conn.execute(
            text("""
            DO $$ BEGIN
                CREATE TYPE public.eventtype AS ENUM (
                    'tab_switch', 'paste_event', 'copy_event', 'devtools_detection',
                    'idle_time', 'burst_typing', 'instant_large_input', 'webcam_anomaly'
                );
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """)
        )
        # Now create all tables
        await conn.run_sync(Base.metadata.create_all)
