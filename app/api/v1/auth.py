"""
EduTrack — Auth API Routes
POST /auth/login, /auth/refresh, /auth/logout, /auth/me, etc.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.core.rate_limit import RateLimit, check_ip_rate_limit
from app.core.redis import redis_client
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserProfileResponse,
)
from app.schemas.common import MessageResponse
from app.services.password_reset_service import PasswordResetService
from app.services.user_service import UserService
from app.services.audit_service import AuditService

router = APIRouter(tags=["Authentication"])
logger = logging.getLogger(__name__)


def _refresh_token_ttl_seconds() -> int:
    return settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400


async def _blacklist_refresh_jti(jti: str | None) -> None:
    if not jti:
        return
    await redis_client.setex(f"blacklist:{jti}", _refresh_token_ttl_seconds(), "1")


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return JWT tokens."""
    await check_ip_rate_limit(
        request,
        RateLimit("auth-login", settings.RATE_LIMIT_LOGIN_PER_MINUTE, 60),
    )
    user = await UserService.authenticate(db, data.email, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_INVALID_CREDENTIALS", "message": "Wrong email or password."},
        )

    access_token = create_access_token(subject=str(user.id), role=user.role)
    refresh_token = create_refresh_token(subject=str(user.id))

    await AuditService.log(db, action="USER_LOGIN", actor_id=user.id, actor_role=user.role)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Refresh the access token using a valid refresh token."""
    await check_ip_rate_limit(
        request,
        RateLimit("auth-refresh", settings.RATE_LIMIT_REFRESH_PER_MINUTE, 60),
    )
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_TOKEN_EXPIRED", "message": "Invalid or expired refresh token."},
        )

    # Check if token is blacklisted
    jti = payload.get("jti")
    if jti and await redis_client.get(f"blacklist:{jti}"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_TOKEN_EXPIRED", "message": "Token has been revoked."},
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

    new_access = create_access_token(subject=str(user.id), role=user.role)
    new_refresh = create_refresh_token(subject=str(user.id))
    await _blacklist_refresh_jti(jti)

    return TokenResponse(access_token=new_access, refresh_token=new_refresh)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    refresh_token: str = "",
    current_user: User = Depends(get_current_user),
):
    """Invalidate refresh token by adding its JTI to Redis blacklist."""
    if refresh_token:
        payload = decode_token(refresh_token)
        if payload and payload.get("jti"):
            await _blacklist_refresh_jti(payload["jti"])
    return MessageResponse(message="Logged out successfully.")


@router.get("/me", response_model=UserProfileResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user's profile."""
    return UserProfileResponse.model_validate(current_user)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Send password reset email."""
    await check_ip_rate_limit(
        request,
        RateLimit("auth-forgot-password", settings.RATE_LIMIT_FORGOT_PASSWORD_PER_HOUR, 3600),
    )
    user = await UserService.get_user_by_email(db, data.email)
    # Always return success to prevent email enumeration
    if user:
        try:
            await PasswordResetService.send_reset_instructions(user)
            await AuditService.log(db, action="PASSWORD_RESET_REQUESTED", actor_id=user.id, actor_role=user.role)
        except Exception:
            logger.exception("Password reset instruction delivery failed for user_id=%s", user.id)
    return MessageResponse(message="If the email exists, a reset link has been sent.")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    data: ResetPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Reset password using a token from email."""
    await check_ip_rate_limit(
        request,
        RateLimit("auth-reset-password", settings.RATE_LIMIT_RESET_PASSWORD_PER_HOUR, 3600),
    )
    user_id = await PasswordResetService.consume_token(data.token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "AUTH_TOKEN_EXPIRED", "message": "Invalid or expired reset token."},
        )

    user = await UserService.get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "AUTH_INVALID_CREDENTIALS", "message": "User not found or inactive."},
        )

    await UserService.reset_password(db, user, data.new_password)
    await AuditService.log(db, action="PASSWORD_RESET_COMPLETED", actor_id=user.id, actor_role=user.role)
    return MessageResponse(message="Password reset successfully.")


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change own password (requires current password)."""
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "AUTH_INVALID_CREDENTIALS", "message": "Current password is incorrect."},
        )
    await UserService.reset_password(db, current_user, data.new_password)
    await AuditService.log(
        db,
        action="PASSWORD_CHANGED",
        actor_id=current_user.id,
        actor_role=current_user.role,
    )
    return MessageResponse(message="Password changed successfully.")
