"""
EduTrack — Report Generation Workers

Tasks:
  - generate_assessment_report: Build a per-assessment PDF/CSV summary.
  - generate_class_report: Build a per-group analytics report.
"""

import asyncio
from uuid import UUID

from sqlalchemy import select, func

from app.workers.celery_app import celery_app
from app.core.database import async_session_factory
from app.models.assessment import Assessment
from app.models.assessment_attempt import AssessmentAttempt


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.workers.report_worker.generate_assessment_report")
def generate_assessment_report(assessment_id: str):
    """Generate and store an assessment performance report."""
    return _run_async(_generate_assessment_report(assessment_id))


async def _generate_assessment_report(assessment_id: str):
    async with async_session_factory() as db:
        assessment = await db.get(Assessment, UUID(assessment_id))
        if not assessment:
            return {"error": "Assessment not found"}

        stats = await db.execute(
            select(
                func.count(AssessmentAttempt.id).label("total"),
                func.avg(AssessmentAttempt.score_percent).label("avg_score"),
                func.max(AssessmentAttempt.score_percent).label("max_score"),
                func.min(AssessmentAttempt.score_percent).label("min_score"),
            ).where(
                AssessmentAttempt.assessment_id == assessment.id,
                AssessmentAttempt.status == "graded",
            )
        )
        row = stats.one()

        # In production this would render a PDF and upload to S3 / local storage
        report_data = {
            "assessment_id": assessment_id,
            "title": assessment.title,
            "total_attempts": row.total,
            "average_score": float(row.avg_score) if row.avg_score else 0.0,
            "max_score": float(row.max_score) if row.max_score else 0.0,
            "min_score": float(row.min_score) if row.min_score else 0.0,
        }

        return {"status": "generated", "report": report_data}


@celery_app.task(name="app.workers.report_worker.generate_class_report")
def generate_class_report(group_id: str):
    """Generate analytics report for a class group."""
    return _run_async(_generate_class_report(group_id))


async def _generate_class_report(group_id: str):
    from app.models.group import Group
    from app.models.group_enrollment import GroupEnrollment

    async with async_session_factory() as db:
        group = await db.get(Group, UUID(group_id))
        if not group:
            return {"error": "Group not found"}

        # Count enrolled students
        student_count = await db.execute(
            select(func.count(GroupEnrollment.id)).where(
                GroupEnrollment.group_id == group.id
            )
        )

        report_data = {
            "group_id": group_id,
            "group_name": group.name,
            "subject": group.subject,
            "enrolled_students": student_count.scalar() or 0,
        }

        return {"status": "generated", "report": report_data}
