"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

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

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "interview_integrity"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
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


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
