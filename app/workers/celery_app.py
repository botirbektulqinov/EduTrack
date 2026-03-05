"""
EduTrack — Celery Application
Broker: Redis  ·  Backend: Redis

Start worker:
    celery -A app.workers.celery_app worker --loglevel=info

Start beat (periodic):
    celery -A app.workers.celery_app beat --loglevel=info
"""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "edu_track",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Auto-discover tasks from worker modules
celery_app.autodiscover_tasks(["app.workers"])

# Periodic beat schedule
celery_app.conf.beat_schedule = {
    "compute-daily-snapshots": {
        "task": "app.workers.analytics_worker.compute_performance_snapshots",
        "schedule": crontab(hour=2, minute=0),  # Every day at 02:00 UTC
    },
    "flag-at-risk-students": {
        "task": "app.workers.analytics_worker.flag_at_risk_students",
        "schedule": crontab(hour=3, minute=0),  # Every day at 03:00 UTC
    },
    "expire-assessments": {
        "task": "app.workers.analytics_worker.expire_assessments",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
    },
}
