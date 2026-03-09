"""Auth routes - login, register, JWT."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_async_session
from app.models.user import User, UserRole
from app.schemas.auth import Token, UserCreate, UserResponse, LoginRequest, SignupRequest
from app.auth.jwt import create_access_token
from app.auth.dependencies import require_roles
from app.auth.password import hash_password, verify_password

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/signup", response_model=Token)
async def signup(
    payload: SignupRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """Public signup: only allowed when no users exist (first admin)."""
    result = await db.execute(select(User))
    existing = result.scalars().first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration is closed. An administrator already exists.",
        )
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.ADMIN,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    settings = get_settings()
    access_token = create_access_token(subject=user.id, role=user.role)
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/register", response_model=UserResponse)
async def register(
    payload: UserCreate,
    db: AsyncSession = Depends(get_async_session),
    _user=Depends(require_roles(UserRole.ADMIN)),
):
    """Register a new user (Admin only)."""
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.post("/init-admin", status_code=status.HTTP_200_OK)
async def init_admin(
    db: AsyncSession = Depends(get_async_session),
):
    """Initialize admin user (admin@example.com / admin123). 
    Creates if doesn't exist, resets password if exists.
    Safe to call multiple times."""
    ADMIN_EMAIL = "admin@example.com"
    ADMIN_PASSWORD = "admin123"
    
    try:
        result = await db.execute(select(User).where(User.email == ADMIN_EMAIL))
        user = result.scalar_one_or_none()
        
        if user:
            # Reset password if user exists
            user.hashed_password = hash_password(ADMIN_PASSWORD)
            user.is_active = True
            await db.commit()
            return {
                "message": f"Admin user password reset successfully",
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            }
        else:
            # Create new admin user
            user = User(
                email=ADMIN_EMAIL,
                hashed_password=hash_password(ADMIN_PASSWORD),
                full_name="Admin",
                role=UserRole.ADMIN,  # Will be converted to 'ADMIN' by TypeDecorator
                is_active=True,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            return {
                "message": "Admin user created successfully",
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            }
    except Exception as e:
        logger.exception("Failed to initialize admin: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize admin user: {str(e)}",
        )


@router.post("/login", response_model=Token)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """Login with JSON body; returns JWT."""
    try:
        result = await db.execute(select(User).where(User.email == payload.email))
        user = result.scalar_one_or_none()
        if not user or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User inactive")
        settings = get_settings()
        access_token = create_access_token(subject=user.id, role=user.role)
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Login failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable. Ensure PostgreSQL is running and POSTGRES_* in interview/.env are correct. Then run: python -m scripts.seed_admin",
        )
