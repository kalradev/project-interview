"""Password hashing and verification using bcrypt (avoids passlib/bcrypt version issues)."""

import bcrypt


def hash_password(password: str) -> str:
    """Hash password with bcrypt. Returns stored hash string."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify plain password against stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False
