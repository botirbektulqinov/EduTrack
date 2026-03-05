"""
EduTrack — Notification Service
In-app and email notification dispatching.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


class NotificationService:

    @staticmethod
    async def create_notification(
        db: AsyncSession,
        user_id: UUID,
        title: str,
        body: Optional[str] = None,
        notification_type: str = "general",
        action_url: Optional[str] = None,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            title=title,
            body=body,
            notification_type=notification_type,
            action_url=action_url,
        )
        db.add(notification)
        await db.flush()
        await db.refresh(notification)
        return notification

    @staticmethod
    async def notify_group(
        db: AsyncSession,
        student_ids: list[UUID],
        title: str,
        body: Optional[str] = None,
        notification_type: str = "general",
        action_url: Optional[str] = None,
    ) -> list[Notification]:
        """Send a notification to all students in a list."""
        notifications = []
        for sid in student_ids:
            n = Notification(
                user_id=sid,
                title=title,
                body=body,
                notification_type=notification_type,
                action_url=action_url,
            )
            db.add(n)
            notifications.append(n)
        await db.flush()
        return notifications
