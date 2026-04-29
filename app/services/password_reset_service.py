"""
Password reset token issuance and verification.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import secrets
from urllib.parse import urlencode
from uuid import UUID

from jose import JWTError, jwt

from app.core.config import settings
from app.core.redis import redis_client
from app.models.user import User
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class PasswordResetService:
    KEY_PREFIX = "password-reset"

    @classmethod
    def build_reset_link(cls, token: str) -> str:
        base = settings.FRONTEND_URL.rstrip("/")
        path = settings.PASSWORD_RESET_URL_PATH
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{base}{path}?{urlencode({'token': token})}"

    @classmethod
    def _redis_key(cls, token: str) -> str:
        return f"{cls.KEY_PREFIX}:{token}"

    @classmethod
    def _build_signed_fallback_token(cls, user: User) -> str:
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
        payload = {
            "sub": str(user.id),
            "type": "password_reset",
            "exp": expire,
            "iat": now,
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    @classmethod
    async def issue_reset_token(cls, user: User) -> str:
        token = secrets.token_urlsafe(48)
        ttl_seconds = settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES * 60
        try:
            await redis_client.setex(cls._redis_key(token), ttl_seconds, str(user.id))
            return token
        except Exception as exc:
            if not settings.ALLOW_PASSWORD_RESET_SIGNED_FALLBACK:
                logger.error("Redis reset-token store unavailable and signed fallback is disabled: %s", exc)
                raise RuntimeError("Password reset token store is unavailable.") from exc
            logger.warning("Redis reset-token store unavailable, using signed fallback token: %s", exc)
            return cls._build_signed_fallback_token(user)

    @classmethod
    async def send_reset_instructions(cls, user: User) -> None:
        token = await cls.issue_reset_token(user)
        reset_link = cls.build_reset_link(token)

        subject = "EduTrack password reset"
        text_body = (
            f"Hello {user.full_name},\n\n"
            f"Use this link to reset your EduTrack password:\n{reset_link}\n\n"
            f"This link expires in {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes."
        )
        html_body = (
            f"<p>Hello {user.full_name},</p>"
            f"<p>Use this link to reset your EduTrack password:</p>"
            f"<p><a href=\"{reset_link}\">{reset_link}</a></p>"
            f"<p>This link expires in {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.</p>"
        )

        sent = await EmailService.send_email(
            to_email=user.email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )

        if not sent:
            logger.warning(
                "Password reset email fallback for %s. Reset link: %s",
                user.email,
                reset_link,
            )

    @classmethod
    async def consume_token(cls, token: str) -> UUID | None:
        user_id = None
        try:
            user_id = await redis_client.get(cls._redis_key(token))
            if user_id:
                await redis_client.delete(cls._redis_key(token))
        except Exception as exc:
            if not settings.ALLOW_PASSWORD_RESET_SIGNED_FALLBACK:
                logger.warning("Redis reset-token lookup unavailable and signed fallback is disabled: %s", exc)
                return None
            logger.warning("Redis reset-token lookup unavailable, trying signed fallback token: %s", exc)

        if not user_id:
            if not settings.ALLOW_PASSWORD_RESET_SIGNED_FALLBACK:
                return None
            try:
                payload = jwt.decode(
                    token,
                    settings.JWT_SECRET_KEY,
                    algorithms=[settings.JWT_ALGORITHM],
                )
                if payload.get("type") != "password_reset":
                    return None
                user_id = payload.get("sub")
            except JWTError:
                return None

        if not user_id:
            return None
        try:
            return UUID(str(user_id))
        except ValueError:
            logger.warning("Invalid password reset token payload encountered")
            return None
