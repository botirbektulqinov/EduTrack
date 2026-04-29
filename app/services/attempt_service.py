"""
EduTrack - Attempt lifecycle helpers.

Shared validation used by REST and WebSocket assessment delivery.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment_attempt import AssessmentAttempt
from app.models.question import Question
from app.models.violation import Violation


ANSWER_MUTABLE_FIELDS = (
    "answer_text",
    "selected_option_ids",
    "matched_pairs",
    "ordered_ids",
    "categorized",
    "hotspot_coords",
    "code_submission",
    "numeric_answer",
    "likert_value",
    "is_flagged",
    "time_spent_seconds",
)

LOCKED_ATTEMPT_STATUSES = {"submitted", "grading", "graded", "terminated"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_attempt_in_progress(attempt: AssessmentAttempt) -> None:
    if attempt.status in LOCKED_ATTEMPT_STATUSES or attempt.status != "in_progress":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "ATTEMPT_ALREADY_SUBMITTED",
                "message": "Cannot modify a submitted, graded, or terminated attempt.",
            },
        )


async def authoritative_remaining_seconds(
    db: AsyncSession,
    attempt: AssessmentAttempt,
    *,
    now: datetime | None = None,
) -> int | None:
    """Compute remaining time from server state instead of trusting the browser."""
    if attempt.time_limit_seconds is None:
        return None

    now = now or utc_now()
    started_at = attempt.started_at
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)

    elapsed_seconds = max(0, int((now - started_at).total_seconds()))
    penalty_seconds = (
        await db.execute(
            select(func.coalesce(func.sum(Violation.time_deducted_seconds), 0)).where(
                Violation.attempt_id == attempt.id,
            )
        )
    ).scalar() or 0
    return max(0, int(attempt.time_limit_seconds - elapsed_seconds - penalty_seconds))


async def sync_attempt_timer(
    db: AsyncSession,
    attempt: AssessmentAttempt,
    *,
    now: datetime | None = None,
) -> int | None:
    remaining = await authoritative_remaining_seconds(db, attempt, now=now)
    if remaining is not None:
        attempt.time_remaining_seconds = remaining
        await db.flush()
    return remaining


async def reject_if_time_expired(db: AsyncSession, attempt: AssessmentAttempt) -> None:
    remaining = await sync_attempt_timer(db, attempt)
    if remaining == 0:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "ATTEMPT_TIME_EXPIRED",
                "message": "The assessment time limit has expired.",
            },
        )


async def validate_questions_belong_to_attempt(
    db: AsyncSession,
    attempt: AssessmentAttempt,
    question_ids: set[UUID],
) -> None:
    if not question_ids:
        return

    valid_ids = set(
        (
            await db.execute(
                select(Question.id).where(
                    Question.assessment_id == attempt.assessment_id,
                    Question.id.in_(question_ids),
                )
            )
        ).scalars()
    )
    invalid_ids = question_ids - valid_ids
    if invalid_ids:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "QUESTION_NOT_IN_ATTEMPT",
                "message": "One or more answers reference questions outside this assessment.",
            },
        )


async def lock_attempt_start_slot(
    db: AsyncSession,
    *,
    assessment_id: UUID,
    student_id: UUID,
) -> None:
    """Serialize start-attempt checks for one student and assessment on PostgreSQL."""
    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
        {"lock_key": f"attempt-start:{assessment_id}:{student_id}"},
    )
