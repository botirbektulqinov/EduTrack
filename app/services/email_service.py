"""
Email delivery helpers.

Uses SMTP directly so password reset can work without a third-party provider.
If SMTP credentials are not configured, delivery falls back to structured logs.
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    @staticmethod
    def _send_sync(message: EmailMessage) -> bool:
        with smtplib.SMTP(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            timeout=settings.SMTP_TIMEOUT_SECONDS,
        ) as smtp:
            smtp.ehlo()
            if settings.SMTP_TLS:
                smtp.starttls()
                smtp.ehlo()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(message)
        return True

    @staticmethod
    async def send_email(
        to_email: str,
        subject: str,
        text_body: str,
        html_body: str | None = None,
    ) -> bool:
        if not settings.SMTP_HOST:
            logger.warning("SMTP host is not configured; skipping email delivery to %s", to_email)
            return False

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM}>"
        message["To"] = to_email
        message.set_content(text_body)
        if html_body:
            message.add_alternative(html_body, subtype="html")

        try:
            return await asyncio.to_thread(EmailService._send_sync, message)
        except Exception:
            logger.exception("Failed to send email to %s", to_email)
            return False
