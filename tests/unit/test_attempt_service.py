import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.models.assessment_attempt import AssessmentAttempt
from app.services.attempt_service import (
    authoritative_remaining_seconds,
    ensure_attempt_in_progress,
)


def attempt(status: str = "in_progress", *, started_at: datetime | None = None) -> AssessmentAttempt:
    return AssessmentAttempt(
        id=uuid.uuid4(),
        assessment_id=uuid.uuid4(),
        student_id=uuid.uuid4(),
        status=status,
        started_at=started_at or datetime.now(timezone.utc),
        time_limit_seconds=1800,
        time_remaining_seconds=1800,
    )


class FakePenaltyResult:
    def __init__(self, seconds: int):
        self.seconds = seconds

    def scalar(self):
        return self.seconds


class FakeDb:
    def __init__(self, penalty_seconds: int = 0):
        self.penalty_seconds = penalty_seconds

    async def execute(self, _statement):
        return FakePenaltyResult(self.penalty_seconds)


def test_ensure_attempt_in_progress_accepts_active_attempt():
    ensure_attempt_in_progress(attempt("in_progress"))


@pytest.mark.parametrize("status", ["submitted", "grading", "graded", "terminated", "not_started"])
def test_ensure_attempt_in_progress_rejects_locked_or_inactive_attempts(status):
    with pytest.raises(HTTPException) as exc:
        ensure_attempt_in_progress(attempt(status))

    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "ATTEMPT_ALREADY_SUBMITTED"


@pytest.mark.asyncio
async def test_authoritative_remaining_seconds_uses_elapsed_time_and_penalties():
    now = datetime(2026, 4, 29, 12, 0, tzinfo=timezone.utc)
    active_attempt = attempt(started_at=now - timedelta(minutes=10))

    remaining = await authoritative_remaining_seconds(
        FakeDb(penalty_seconds=120),
        active_attempt,
        now=now,
    )

    assert remaining == 1080


@pytest.mark.asyncio
async def test_authoritative_remaining_seconds_never_goes_negative():
    now = datetime(2026, 4, 29, 12, 0, tzinfo=timezone.utc)
    active_attempt = attempt(started_at=now - timedelta(hours=2))

    remaining = await authoritative_remaining_seconds(
        FakeDb(penalty_seconds=300),
        active_attempt,
        now=now,
    )

    assert remaining == 0
