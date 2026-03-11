"""Seed or reset admin user. Run: python -m scripts.seed_admin.
   Creates admin@example.com with password admin123, or resets password if user exists."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.config import get_settings
from app.database.base import Base
from app import models  # noqa: F401 - register all models with Base
from app.models.user import User, UserRole

ADMIN_EMAIL = "deevanshukalra30@gmail.com"
ADMIN_PASSWORD = "Pompom@6969"


def hash_password(password: str) -> str:
    """Hash compatible with passlib verify (bcrypt)."""
    import bcrypt
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _engine_connect_args(settings) -> dict:
    """Enable SSL for asyncpg when using cloud DB (Render, Supabase, etc.)."""
    url = (settings.database_url_env or "") + (settings.database_url or "")
    if any(h in url for h in ("render.com", "dpg-", "supabase", "railway", "neon.tech", "amazonaws.com")):
        return {"ssl": True}
    return {}


async def main():
    settings = get_settings()
    if settings.database_url_env and settings.database_url_env.strip():
        print("Using DB: from DATABASE_URL")
    else:
        print(f"Using DB: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")
    engine = create_async_engine(
        settings.database_url,
        connect_args=_engine_connect_args(settings),
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        result = await db.execute(select(User).where(User.email == ADMIN_EMAIL))
        user = result.scalar_one_or_none()
        if user:
            user.hashed_password = hash_password(ADMIN_PASSWORD)
            user.is_active = True
            await db.commit()
            print(f"Reset password for {ADMIN_EMAIL} to: {ADMIN_PASSWORD}")
        else:
            user = User(
                email=ADMIN_EMAIL,
                hashed_password=hash_password(ADMIN_PASSWORD),
                full_name="Admin",
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(user)
            await db.commit()
            print(f"Created {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
