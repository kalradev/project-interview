"""Auth dependencies - role-based access."""

from typing import Callable

from fastapi import Depends, HTTPException, status

from app.auth.jwt import get_current_user_required
from app.models.user import UserRole

# Type for current user from JWT
CurrentUser = dict  # {"sub": str, "role": UserRole}


def require_roles(*allowed_roles: UserRole) -> Callable:
    """Dependency factory: require user to have one of the allowed roles."""

    async def _require(
        current_user: CurrentUser = Depends(get_current_user_required),
    ) -> CurrentUser:
        if current_user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _require
