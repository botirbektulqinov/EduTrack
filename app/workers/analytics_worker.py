"""
EduTrack — Analytics Background Workers

Tasks:
  - compute_performance_snapshots: Nightly aggregation of student scores.
  - flag_at_risk_students: Identify students whose performance is declining.
  - expire_assessments: Terminate in-progress attempts past their window.
"""

import asyncio
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, and_

from app.workers.celery_app import celery_app
from app.core.database import async_session_factory
from app.models.assessment import Assessment
from app.models.assessment_attempt import AssessmentAttempt
from app.models.performance_snapshot import PerformanceSnapshot
from app.models.user import User
from app.models.group_enrollment import GroupEnrollment


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.workers.analytics_worker.compute_performance_snapshots")
def compute_performance_snapshots():
    """Compute daily PerformanceSnapshot rows for every active student."""
    return _run_async(_compute_performance_snapshots())


async def _compute_performance_snapshots():
    async with async_session_factory() as db:
        # All students that have at least one graded attempt
        students = await db.execute(
            select(AssessmentAttempt.student_id).where(
                AssessmentAttempt.status == "graded"
            ).distinct()
        )

        now = datetime.now(timezone.utc)
        count = 0

        for (student_id,) in students:
            # Aggregate scores
            stats = await db.execute(
                select(
                    func.avg(AssessmentAttempt.score_percent).label("avg_score"),
                    func.max(AssessmentAttempt.score_percent).label("best_score"),
                    func.min(AssessmentAttempt.score_percent).label("worst_score"),
                    func.count(AssessmentAttempt.id).label("total_attempts"),
                ).where(
                    AssessmentAttempt.student_id == student_id,
                    AssessmentAttempt.status == "graded",
                )
            )
            row = stats.one()

            # Compute improvement rate (last 30 days vs prior 30 days)
            thirty_days_ago = now - timedelta(days=30)
            sixty_days_ago = now - timedelta(days=60)

            recent = await db.execute(
                select(func.avg(AssessmentAttempt.score_percent)).where(
                    AssessmentAttempt.student_id == student_id,
                    AssessmentAttempt.status == "graded",
                    AssessmentAttempt.submitted_at >= thirty_days_ago,
                )
            )
            recent_avg = recent.scalar() or 0.0

            prior = await db.execute(
                select(func.avg(AssessmentAttempt.score_percent)).where(
                    AssessmentAttempt.student_id == student_id,
                    AssessmentAttempt.status == "graded",
                    AssessmentAttempt.submitted_at >= sixty_days_ago,
                    AssessmentAttempt.submitted_at < thirty_days_ago,
                )
            )
            prior_avg = prior.scalar()
            improvement_rate = (recent_avg - prior_avg) if prior_avg else 0.0

            # Count passed attempts (score >= 50%)
            passed_result = await db.execute(
                select(func.count(AssessmentAttempt.id)).where(
                    AssessmentAttempt.student_id == student_id,
                    AssessmentAttempt.status == "graded",
                    AssessmentAttempt.score_percent >= 50.0,
                )
            )
            passed_count = passed_result.scalar() or 0

            # Count violations
            from app.models.violation import Violation
            violation_total = (await db.execute(
                select(func.count(Violation.id)).where(
                    Violation.student_id == student_id,
                )
            )).scalar() or 0

            snapshot = PerformanceSnapshot(
                student_id=student_id,
                period_type="daily",
                period_label=now.strftime("%Y-%m-%d"),
                assessments_taken=row.total_attempts,
                assessments_passed=passed_count,
                avg_score=row.avg_score or 0.0,
                best_score=row.best_score or 0.0,
                worst_score=row.worst_score or 0.0,
                improvement_rate=improvement_rate,
                violation_total=violation_total,
                at_risk=bool(row.avg_score and row.avg_score < 50.0),
                computed_at=now,
            )
            db.add(snapshot)
            count += 1

        await db.commit()
        return {"snapshots_created": count}


@celery_app.task(name="app.workers.analytics_worker.flag_at_risk_students")
def flag_at_risk_students():
    """Flag students whose average score is below threshold or declining."""
    return _run_async(_flag_at_risk_students())


async def _flag_at_risk_students():
    async with async_session_factory() as db:
        # Students with avg < 50% across last 30 days
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

        at_risk = await db.execute(
            select(
                AssessmentAttempt.student_id,
                func.avg(AssessmentAttempt.score_percent).label("avg"),
            ).where(
                AssessmentAttempt.status == "graded",
                AssessmentAttempt.submitted_at >= thirty_days_ago,
            ).group_by(AssessmentAttempt.student_id).having(
                func.avg(AssessmentAttempt.score_percent) < 50.0
            )
        )

        flagged = []
        for student_id, avg in at_risk:
            flagged.append(str(student_id))

            # Create/update notification
            from app.services.notification_service import NotificationService
            await NotificationService.create_notification(
                db=db,
                user_id=student_id,
                title="Performance Alert",
                body=f"Your average score over the last 30 days is {avg:.1f}%. "
                     "Please consult your teacher for support.",
                notification_type="warning",
            )

        await db.commit()
        return {"at_risk_students": len(flagged), "student_ids": flagged}


# ── Expire Assessments ──

@celery_app.task(name="app.workers.analytics_worker.expire_assessments")
def expire_assessments():
    """Terminate in-progress attempts whose assessment window has passed."""
    return _run_async(_expire_assessments())


async def _expire_assessments():
    async with async_session_factory() as db:
        now = datetime.now(timezone.utc)

        # Find in-progress attempts where the assessment's available_until has passed
        result = await db.execute(
            select(AssessmentAttempt)
            .join(Assessment, AssessmentAttempt.assessment_id == Assessment.id)
            .where(
                AssessmentAttempt.status == "in_progress",
                Assessment.available_until.isnot(None),
                Assessment.available_until < now,
            )
        )
        expired_attempts = result.scalars().all()

        count = 0
        for attempt in expired_attempts:
            attempt.status = "submitted"
            attempt.submitted_at = now
            attempt.termination_reason = "ASSESSMENT_WINDOW_EXPIRED"
            count += 1

        await db.commit()
        return {"expired_attempts": count}
