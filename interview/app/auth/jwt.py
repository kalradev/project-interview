"""JWT token creation and validation."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings
from app.models.user import User, UserRole

security = HTTPBearer(auto_error=False)


def create_access_token(
    subject: str | UUID,
    role: UserRole,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create JWT access token."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "role": role.value,
        "type": "access",
    }
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_interview_link_token(subject: str | UUID) -> str:
    """Create a short-lived JWT for the interview link (email link). Valid for interview_link_expire_days."""
    settings = get_settings()
    days = getattr(settings, "interview_link_expire_days", 7)
    expire = datetime.now(timezone.utc) + timedelta(days=days)
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "type": "interview_link",
    }
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_interview_link_token(token: str) -> dict:
    """Decode interview link JWT. Returns payload with sub (user_id). Raises HTTPException if invalid."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "interview_link":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid link",
            )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired link",
        ) from e


def decode_token(token: str) -> dict:
    """Decode and validate JWT token. Raises HTTPException on invalid token."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """
    Dependency that returns current user payload from JWT.
    Use with optional auth; for required auth use get_current_user_required.
    """
    if not credentials:
        return None
    payload = decode_token(credentials.credentials)
    return {
        "sub": payload["sub"],
        "role": UserRole(payload["role"]),
    }


async def get_current_user_required(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Dependency that requires valid JWT and returns user payload."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await get_current_user(credentials)
