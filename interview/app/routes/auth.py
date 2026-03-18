"""Auth routes - login, register, JWT."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_async_session
from app.models.user import User, UserRole
from app.schemas.auth import Token, UserCreate, UserResponse, LoginRequest, SignupRequest, ChangePasswordRequest
from app.auth.jwt import create_access_token
from app.auth.dependencies import require_roles
from app.auth.jwt import get_current_user_required
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
            # Create new admin user using raw SQL to bypass TypeDecorator issues
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
                    "role": "ADMIN",  # Direct uppercase string to match DB enum
                    "is_active": True
                }
            )
            await db.commit()
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


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_async_session),
):
    """Return the currently authenticated user's details (for admin profile). Optimized with timeout."""
    import asyncio
    from sqlalchemy.orm import load_only
    
    user_id = uuid.UUID(current_user["sub"])
    try:
        # Only fetch needed columns for profile page
        result = await asyncio.wait_for(
            db.execute(
                select(User)
                .options(load_only(User.id, User.email, User.full_name, User.role, User.is_active, User.created_at))
                .where(User.id == user_id)
            ),
            timeout=2.0,  # 2 second timeout
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user
    except asyncio.TimeoutError:
        logger.error(f"Get current user info timed out for {user_id}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database query timeout. Please try again.",
        )


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_async_session),
):
    """Change password for the authenticated user. Requires current password."""
    user_id = uuid.UUID(current_user["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    user.hashed_password = hash_password(payload.new_password)
    await db.commit()
    return {"message": "Password updated successfully"}


@router.post("/login", response_model=Token)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """Login with JSON body; returns JWT. Optimized with raw SQL for speed."""
    import asyncio
    import time
    start_time = time.time()
    try:
        # Use raw SQL query for maximum performance (bypasses ORM overhead)
        # Only fetch the columns we need: id, hashed_password, is_active, role
        result = await asyncio.wait_for(
            db.execute(
                sql_text("""
                    SELECT id, hashed_password, is_active, role
                    FROM users
                    WHERE email = :email
                    LIMIT 1
                """),
                {"email": payload.email}
            ),
            timeout=2.0,  # 2 second timeout - fail fast
        )
        row = result.first()
        if not row:
            # Use same error message for both cases to prevent user enumeration
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )
        
        user_id, hashed_password, is_active, role_str = row
        
        # Verify password
        if not verify_password(payload.password, hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )
        
        if not is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User inactive")
        
        # Convert role string to UserRole enum (normalize to lowercase)
        role = UserRole(role_str.lower()) if isinstance(role_str, str) else UserRole.CANDIDATE
        
        settings = get_settings()
        access_token = create_access_token(subject=user_id, role=role)
        elapsed = time.time() - start_time
        if elapsed > 1.0:  # Log if login takes more than 1 second
            logger.warning(f"Login took {elapsed:.2f}s for {payload.email}")
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )
    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        logger.error(f"Login query timed out after 2 seconds (total: {elapsed:.2f}s) for {payload.email}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection timeout. Please try again.",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Login failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable. Check PostgreSQL is running and DATABASE_URL (or POSTGRES_*) is correct. "
            "On Render: set DATABASE_URL in the Web Service environment to the Internal Database URL from your PostgreSQL service, then redeploy.",
        )
