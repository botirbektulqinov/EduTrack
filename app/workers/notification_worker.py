"""
EduTrack — Notification Background Workers

Tasks:
  - send_email_notification: Async email dispatch.
  - send_bulk_notifications: Send notifications to many users.
"""

import asyncio

from app.workers.celery_app import celery_app
from app.core.database import async_session_factory
from app.services.notification_service import NotificationService


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.workers.notification_worker.send_email_notification")
def send_email_notification(user_email: str, subject: str, body: str):
    """
    Send an email notification.
    In production, integrate with SMTP / SendGrid / SES here.
    """
    # Placeholder — log and return
    return {
        "status": "sent",
        "to": user_email,
        "subject": subject,
    }


@celery_app.task(name="app.workers.notification_worker.send_bulk_notifications")
def send_bulk_notifications(user_ids: list[str], title: str, body: str, notification_type: str = "info"):
    """Create in-app notifications for a list of users."""
    return _run_async(_send_bulk(user_ids, title, body, notification_type))


async def _send_bulk(user_ids: list[str], title: str, body: str, notification_type: str):
    from uuid import UUID
    async with async_session_factory() as db:
        for uid in user_ids:
            await NotificationService.create_notification(
                db=db,
                user_id=UUID(uid),
                title=title,
                body=body,
                notification_type=notification_type,
            )
        await db.commit()
    return {"notifications_created": len(user_ids)}
