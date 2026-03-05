"""
EduTrack — API Dependencies
FastAPI dependency injection: current user, DB session, role checks.
"""

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.services.user_service import UserService

security_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate the current user from the JWT token."""
    token = credentials.credentials
    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_TOKEN_EXPIRED", "message": "Invalid or expired token."},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_TOKEN_EXPIRED", "message": "Invalid token payload."},
        )

    user = await UserService.get_user_by_id(db, UUID(user_id))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_INVALID_CREDENTIALS", "message": "User not found or inactive."},
        )

    return user


def require_role(*roles: str):
    """Dependency factory: enforce required roles."""
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                    "message": f"Requires one of: {', '.join(roles)}",
                },
            )
        return current_user
    return role_checker


# Convenience dependencies
get_admin_user = require_role("admin")
get_teacher_user = require_role("admin", "teacher")
get_student_user = require_role("student")
get_any_authenticated_user = require_role("admin", "teacher", "student")
get_any_authenticated_user = require_role("admin", "teacher", "student")
