"""FastAPI application entry point."""

import logging
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text as sql_text

from app.config import get_settings
from app.database import init_db
from app.models.user import User
from app.auth.password import hash_password
from app.routes import auth, sessions, events, integrity, interview, websocket_router, admin_candidates, admin_resumes, candidate

logger = logging.getLogger(__name__)


async def _ensure_admin_user() -> None:
    """Ensure admin user exists. Creates it if missing."""
    from app.database import async_session_factory
    
    ADMIN_EMAIL = "admin@example.com"
    ADMIN_PASSWORD = "admin123"
    
    try:
        async with async_session_factory() as db:
            result = await db.execute(select(User).where(User.email == ADMIN_EMAIL))
            user = result.scalar_one_or_none()
            
            if not user:
                # Create admin user using raw SQL to avoid TypeDecorator issues
                user_id = uuid.uuid4()
                hashed_pwd = hash_password(ADMIN_PASSWORD)
                await db.execute(
                    sql_text("""
                        INSERT INTO users (id, email, hashed_password, full_name, role, is_active, created_at, updated_at)
                        VALUES (:id::uuid, :email, :hashed_password, :full_name, :role::userrole, :is_active, NOW(), NOW())
                    """),
                    {
                        "id": str(user_id),
                        "email": ADMIN_EMAIL,
                        "hashed_password": hashed_pwd,
                        "full_name": "Admin",
                        "role": "ADMIN",
                        "is_active": True
                    }
                )
                await db.commit()
                logger.info(f"Admin user created automatically: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    except Exception as e:
        logger.warning(f"Failed to ensure admin user exists: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown."""
    try:
        await init_db()
        # Automatically create admin user if it doesn't exist
        await _ensure_admin_user()
    except Exception as e:
        err_msg = str(e).lower()
        if (
            "password" in err_msg
            or "connection" in err_msg
            or "refused" in err_msg
            or "timeout" in err_msg
            or (type(e).__module__ == "asyncpg.exceptions")
        ):
            logger.warning(
                "Database connection failed at startup: %s. "
                "Check POSTGRES_* in .env and that PostgreSQL is running. "
                "Server starting anyway; API requests that need the DB will fail.",
                e,
            )
        else:
            logger.warning(
                "Database initialization failed: %s. "
                "Server starting anyway; API requests that need the DB will fail.",
                e,
            )
    yield


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description="Secure interview monitoring agent - detects AI-assisted cheating",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    origins = ["*"] if settings.debug else []
    if not origins and settings.cors_origins.strip():
        origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    if settings.environment == "development":
        origins.append("null")  # Electron file:// sends Origin: null
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth.router, prefix=f"{settings.api_v1_prefix}/auth", tags=["Auth"])
    app.include_router(sessions.router, prefix=f"{settings.api_v1_prefix}/sessions", tags=["Sessions"])
    app.include_router(events.router, prefix=f"{settings.api_v1_prefix}/events", tags=["Events"])
    app.include_router(integrity.router, prefix=f"{settings.api_v1_prefix}/integrity", tags=["Integrity"])
    app.include_router(interview.router, prefix=f"{settings.api_v1_prefix}/interview", tags=["Interview"])
    app.include_router(candidate.router, prefix=f"{settings.api_v1_prefix}/candidate", tags=["Candidate"])
    app.include_router(admin_candidates.router, prefix=f"{settings.api_v1_prefix}/admin/candidates", tags=["Admin Candidates"])
    app.include_router(admin_resumes.router, prefix=f"{settings.api_v1_prefix}/admin/resumes", tags=["Admin Resumes"])
    app.include_router(websocket_router.router, prefix=f"{settings.api_v1_prefix}/ws", tags=["WebSocket"])
    uploads_dir = Path(settings.upload_photos_dir)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    Path(settings.upload_videos_dir).mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir.parent)), name="uploads")
    return app


app = create_application()


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}
