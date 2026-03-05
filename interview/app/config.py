"""Application configuration using Pydantic Settings.

Database: set either DATABASE_URL (e.g. from Render/Supabase) or all of
POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB.
No localhost is hardcoded; production must use environment variables.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "Interview Integrity Agent"
    debug: bool = False
    environment: str = "development"

    # API
    api_v1_prefix: str = "/api/v1"
    # CORS: comma-separated origins (e.g. https://dashboard.example.com). If set, used when debug=False.
    cors_origins: str = ""

    # JWT
    secret_key: str = "change-me-in-production-use-long-random-string"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # PostgreSQL – all from environment (no hardcoded localhost).
    # Option A: set DATABASE_URL (e.g. postgresql://user:pass@host:5432/dbname) – used by Render, Supabase, etc.
    # Option B: set POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
    database_url_env: str | None = Field(default=None, alias="DATABASE_URL")
    postgres_host: str = Field(default="", description="From POSTGRES_HOST")
    postgres_port: int = Field(default=5432, description="From POSTGRES_PORT")
    postgres_user: str = Field(default="", description="From POSTGRES_USER")
    postgres_password: str = Field(default="", description="From POSTGRES_PASSWORD")
    postgres_db: str = Field(default="", description="From POSTGRES_DB")

    @property
    def database_url(self) -> str:
        """Async connection URL for SQLAlchemy (postgresql+asyncpg://)."""
        if self.database_url_env and self.database_url_env.strip():
            return _to_async_url(self.database_url_env.strip())
        return _build_url(
            self.postgres_host,
            self.postgres_port,
            self.postgres_user,
            self.postgres_password,
            self.postgres_db,
            async_driver=True,
        )

    @property
    def database_url_sync(self) -> str:
        """Sync connection URL for migrations/scripts (postgresql://)."""
        if self.database_url_env and self.database_url_env.strip():
            return _to_sync_url(self.database_url_env.strip())
        return _build_url(
            self.postgres_host,
            self.postgres_port,
            self.postgres_user,
            self.postgres_password,
            self.postgres_db,
            async_driver=False,
        )

    # OpenAI (interview agent)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Email (invite: credentials + interview time + setup link)
    # Option A: Brevo (testing) – set BREVO_API_KEY and BREVO_FROM_EMAIL
    brevo_api_key: str = ""
    brevo_from_email: str = ""  # Sender email (verify in Brevo if needed)
    # Option B: SMTP (for later production) – set SMTP_* when not using Brevo
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    # Link to download Interview Agent setup (e.g. your server or GitHub release)
    setup_app_download_url: str = "https://github.com/your-org/interview-agent/releases/latest"
    # Dir to store uploaded candidate photos (relative to app or absolute)
    upload_photos_dir: str = "uploads/photos"
    upload_videos_dir: str = "uploads/videos"

    # ML
    ai_classifier_path: str = "app/ml/ai_classifier.pkl"
    integrity_base_score: int = 100
    penalty_tab_switch: int = 10
    penalty_paste: int = 15
    penalty_ai_probability: int = 40
    penalty_webcam_anomaly: int = 20


def _to_async_url(url_str: str) -> str:
    """Convert postgresql:// or postgres:// to postgresql+asyncpg://."""
    if "postgresql+asyncpg://" in url_str:
        return url_str
    if url_str.startswith("postgres://"):
        return url_str.replace("postgres://", "postgresql+asyncpg://", 1)
    if url_str.startswith("postgresql://"):
        return url_str.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url_str


def _to_sync_url(url_str: str) -> str:
    """Ensure postgresql:// (sync) – strip +asyncpg if present."""
    if "postgresql+asyncpg://" in url_str:
        return url_str.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url_str


def _build_url(
    host: str,
    port: int,
    user: str,
    password: str,
    db: str,
    *,
    async_driver: bool,
) -> str:
    """Build connection URL from components. Raises if required fields are missing."""
    if not host or not user or not db:
        raise ValueError(
            "Database config missing. Set either DATABASE_URL or all of: "
            "POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB (and optionally POSTGRES_PORT)."
        )
    scheme = "postgresql+asyncpg" if async_driver else "postgresql"
    return f"{scheme}://{user}:{password}@{host}:{port}/{db}"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
