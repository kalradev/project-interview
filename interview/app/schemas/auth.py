"""Auth-related Pydantic schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.models.user import UserRole


class UserCreate(BaseModel):
    """Schema for user registration."""

    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.CANDIDATE


class LoginRequest(BaseModel):
    """Schema for login."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for user in responses."""

    id: UUID
    email: str
    full_name: Optional[str] = None
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenPayload(BaseModel):
    """JWT payload schema."""

    sub: str
    exp: datetime
    role: UserRole
    type: str = "access"


class Token(BaseModel):
    """Token response schema."""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int
