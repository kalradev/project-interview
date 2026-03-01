"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import init_db
from app.routes import auth, sessions, events, integrity, interview, websocket_router, admin_candidates, admin_resumes, candidate


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown."""
    await init_db()
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
