import asyncio
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy import func, select

from app.models.assessment_attempt import AssessmentAttempt
from app.models.student_answer import StudentAnswer
from tests.integration.factories import (
    PASSWORD,
    create_assessment_for_window,
    create_attempt,
    seed_core_data,
)

pytestmark = pytest.mark.integration


async def login(client, email: str, password: str = PASSWORD) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


async def start_attempt(client, token: str, access_token) -> dict:
    response = await client.post(
        f"/api/v1/student/take/{access_token}/start",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    return response.json()["data"]


@pytest.mark.asyncio
async def test_student_can_start_save_and_submit_assessment(api_client, db_session_factory):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)

    token = await login(api_client, seed.student.email)
    started = await start_attempt(api_client, token, seed.assessment.access_token)
    attempt_id = started["attempt_id"]

    save_response = await api_client.post(
        f"/api/v1/student/attempts/{attempt_id}/save",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "answers": [
                {
                    "question_id": str(seed.question.id),
                    "selected_option_ids": [str(seed.correct_option.id)],
                }
            ]
        },
    )
    submit_response = await api_client.post(
        f"/api/v1/student/attempts/{attempt_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert save_response.status_code == 200
    assert submit_response.status_code == 200
    assert submit_response.json()["data"]["score_percent"] == 100


@pytest.mark.asyncio
async def test_student_can_validate_own_assessment_token_when_enrolled(api_client, db_session_factory):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)

    token = await login(api_client, seed.student.email)
    response = await api_client.get(
        f"/api/v1/student/take/{seed.assessment.access_token}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["title"] == seed.assessment.title


@pytest.mark.asyncio
async def test_student_cannot_validate_token_for_group_not_enrolled(api_client, db_session_factory):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)

    token = await login(api_client, seed.student.email)
    response = await api_client.get(
        f"/api/v1/student/take/{seed.other_assessment.access_token}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "STUDENT_NOT_IN_GROUP"


@pytest.mark.asyncio
async def test_start_before_and_after_availability_window_is_blocked(api_client, db_session_factory):
    now = datetime.now(timezone.utc)
    async with db_session_factory() as db:
        seed = await seed_core_data(db)
        future = await create_assessment_for_window(
            db,
            seed,
            available_from=now + timedelta(hours=1),
            available_until=now + timedelta(hours=2),
        )
        expired = await create_assessment_for_window(
            db,
            seed,
            available_from=now - timedelta(hours=2),
            available_until=now - timedelta(hours=1),
        )

    token = await login(api_client, seed.student.email)
    before_response = await api_client.post(
        f"/api/v1/student/take/{future.access_token}/start",
        headers={"Authorization": f"Bearer {token}"},
    )
    after_response = await api_client.post(
        f"/api/v1/student/take/{expired.access_token}/start",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert before_response.status_code == 403
    assert before_response.json()["code"] == "ASSESSMENT_NOT_YET_AVAILABLE"
    assert after_response.status_code == 403
    assert after_response.json()["code"] == "ASSESSMENT_EXPIRED"


@pytest.mark.asyncio
async def test_student_cannot_exceed_max_attempts(api_client, db_session_factory):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)

    token = await login(api_client, seed.student.email)
    await start_attempt(api_client, token, seed.assessment.access_token)
    second_start = await api_client.post(
        f"/api/v1/student/take/{seed.assessment.access_token}/start",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert second_start.status_code == 403
    assert second_start.json()["code"] == "ASSESSMENT_MAX_ATTEMPTS"


@pytest.mark.asyncio
async def test_concurrent_start_does_not_exceed_max_attempts(api_client, db_session_factory):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)

    token = await login(api_client, seed.student.email)

    async def start_once():
        return await api_client.post(
            f"/api/v1/student/take/{seed.assessment.access_token}/start",
            headers={"Authorization": f"Bearer {token}"},
        )

    first, second = await asyncio.gather(start_once(), start_once())
    statuses = sorted([first.status_code, second.status_code])

    async with db_session_factory() as db:
        attempt_count = (
            await db.execute(
                select(func.count(AssessmentAttempt.id)).where(
                    AssessmentAttempt.assessment_id == seed.assessment.id,
                    AssessmentAttempt.student_id == seed.student.id,
                )
            )
        ).scalar_one()

    assert statuses == [200, 403]
    assert attempt_count == 1


@pytest.mark.asyncio
async def test_submitted_attempt_is_locked_and_double_submit_conflicts(api_client, db_session_factory):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)

    token = await login(api_client, seed.student.email)
    started = await start_attempt(api_client, token, seed.assessment.access_token)
    attempt_id = started["attempt_id"]

    assert started["server_token"]
    assert UUID(started["server_token"])

    first_submit = await api_client.post(
        f"/api/v1/student/attempts/{attempt_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    second_submit = await api_client.post(
        f"/api/v1/student/attempts/{attempt_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    save_after_submit = await api_client.post(
        f"/api/v1/student/attempts/{attempt_id}/save",
        headers={"Authorization": f"Bearer {token}"},
        json={"answers": [{"question_id": str(seed.question.id), "answer_text": "late"}]},
    )

    assert first_submit.status_code == 200
    assert second_submit.status_code == 409
    assert save_after_submit.status_code == 409


@pytest.mark.asyncio
async def test_terminated_attempt_cannot_be_saved_or_submitted(api_client, db_session_factory):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)
        terminated = await create_attempt(
            db,
            assessment_id=seed.assessment.id,
            student_id=seed.student.id,
            status="terminated",
        )

    token = await login(api_client, seed.student.email)
    save_response = await api_client.post(
        f"/api/v1/student/attempts/{terminated.id}/save",
        headers={"Authorization": f"Bearer {token}"},
        json={"answers": [{"question_id": str(seed.question.id), "answer_text": "late"}]},
    )
    submit_response = await api_client.post(
        f"/api/v1/student/attempts/{terminated.id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert save_response.status_code == 409
    assert submit_response.status_code == 409


@pytest.mark.asyncio
async def test_student_cannot_save_question_from_another_assessment(api_client, db_session_factory):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)

    token = await login(api_client, seed.student.email)
    started = await start_attempt(api_client, token, seed.assessment.access_token)
    response = await api_client.post(
        f"/api/v1/student/attempts/{started['attempt_id']}/save",
        headers={"Authorization": f"Bearer {token}"},
        json={"answers": [{"question_id": str(seed.other_question.id), "answer_text": "bad"}]},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "QUESTION_NOT_IN_ATTEMPT"


@pytest.mark.asyncio
async def test_student_cannot_modify_someone_elses_attempt(api_client, db_session_factory):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)
        other_attempt = await create_attempt(
            db,
            assessment_id=seed.assessment.id,
            student_id=seed.other_student.id,
            status="in_progress",
        )

    token = await login(api_client, seed.student.email)
    response = await api_client.post(
        f"/api/v1/student/attempts/{other_attempt.id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "ATTEMPT_NOT_FOUND"


@pytest.mark.asyncio
async def test_submit_persists_answer_and_grades_once(api_client, db_session_factory):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)

    token = await login(api_client, seed.student.email)
    started = await start_attempt(api_client, token, seed.assessment.access_token)
    attempt_id = started["attempt_id"]
    await api_client.post(
        f"/api/v1/student/attempts/{attempt_id}/save",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "answers": [
                {
                    "question_id": str(seed.question.id),
                    "selected_option_ids": [str(seed.correct_option.id)],
                }
            ]
        },
    )
    await api_client.post(
        f"/api/v1/student/attempts/{attempt_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )

    async with db_session_factory() as db:
        attempt = await db.get(AssessmentAttempt, UUID(attempt_id))
        answers = (
            await db.execute(select(StudentAnswer).where(StudentAnswer.attempt_id == UUID(attempt_id)))
        ).scalars().all()

    assert attempt.status == "graded"
    assert attempt.score_percent == 100
    assert len(answers) == 1
    assert answers[0].score_awarded == 10
