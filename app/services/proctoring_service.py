"""
EduTrack — Proctoring Service
Violation handling, termination logic.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment
from app.models.assessment_attempt import AssessmentAttempt
from app.models.violation import Violation
from app.services.grading_service import GradingService


class ProctoringService:

    @staticmethod
    async def record_violation(
        db: AsyncSession,
        attempt: AssessmentAttempt,
        assessment: Assessment,
        violation_type: str,
        time_remaining: Optional[int] = None,
        browser_info: Optional[dict] = None,
        ip_address: Optional[str] = None,
    ) -> dict:
        """
        Record a proctoring violation.
        Returns action dict: {action: "warning"|"terminate", violation_count, time_deducted}
        """
        # Increment violation count
        attempt.violation_count += 1
        new_count = attempt.violation_count

        # Calculate time deduction
        time_penalty_seconds = assessment.time_penalty_minutes * 60
        if attempt.time_remaining_seconds is not None:
            attempt.time_remaining_seconds = max(0, attempt.time_remaining_seconds - time_penalty_seconds)

        # Create violation record
        violation = Violation(
            attempt_id=attempt.id,
            student_id=attempt.student_id,
            assessment_id=assessment.id,
            violation_type=violation_type,
            occurred_at=datetime.now(timezone.utc),
            time_remaining_at_event=time_remaining,
            time_deducted_seconds=time_penalty_seconds,
            violation_count_after=new_count,
            browser_info=browser_info,
            ip_address=ip_address,
        )
        db.add(violation)

        # Check if max violations reached → terminate
        if new_count >= assessment.max_violations:
            attempt.status = "terminated"
            attempt.termination_reason = f"MAX_VIOLATIONS ({new_count}/{assessment.max_violations})"
            attempt.score_raw = 0
            attempt.score_percent = 0
            attempt.grade = "FAIL"
            attempt.submitted_at = datetime.now(timezone.utc)

            await db.flush()
            return {
                "action": "terminate",
                "violation_count": new_count,
                "max_violations": assessment.max_violations,
                "time_deducted_seconds": time_penalty_seconds,
                "reason": "MAX_VIOLATIONS",
            }

        await db.flush()
        return {
            "action": "warning",
            "violation_count": new_count,
            "max_violations": assessment.max_violations,
            "time_deducted_seconds": time_penalty_seconds,
            "new_time_remaining": attempt.time_remaining_seconds,
        }

    @staticmethod
    async def get_violations_for_attempt(
        db: AsyncSession,
        attempt_id: UUID,
    ) -> list[Violation]:
        result = await db.execute(
            select(Violation)
            .where(Violation.attempt_id == attempt_id)
            .order_by(Violation.occurred_at)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_violations_for_assessment(
        db: AsyncSession,
        assessment_id: UUID,
    ) -> list[Violation]:
        result = await db.execute(
            select(Violation)
            .where(Violation.assessment_id == assessment_id)
            .order_by(Violation.occurred_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_violation_stats(db: AsyncSession, assessment_id: UUID) -> dict:
        """Get violation type breakdown for an assessment."""
        result = await db.execute(
            select(
                Violation.violation_type,
                func.count(Violation.id).label("count")
            )
            .where(Violation.assessment_id == assessment_id)
            .group_by(Violation.violation_type)
        )
        return {row.violation_type: row.count for row in result}
