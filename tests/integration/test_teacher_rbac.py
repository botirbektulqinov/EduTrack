import pytest

from app.models.student_answer import StudentAnswer
from tests.integration.factories import PASSWORD, create_attempt, seed_core_data

pytestmark = pytest.mark.integration


async def login(client, email: str, password: str = PASSWORD) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_teacher_can_access_own_group_analytics(api_client, db_session_factory):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)

    token = await login(api_client, seed.teacher.email)
    response = await api_client.get(
        f"/api/v1/teacher/groups/{seed.group.id}/analytics",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["group_id"] == str(seed.group.id)


@pytest.mark.asyncio
async def test_teacher_can_view_attempts_for_own_assessment(api_client, db_session_factory):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)
        await create_attempt(db, assessment_id=seed.assessment.id, student_id=seed.student.id)

    token = await login(api_client, seed.teacher.email)
    response = await api_client.get(
        f"/api/v1/teacher/assessments/{seed.assessment.id}/attempts",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["meta"]["total"] == 1


@pytest.mark.asyncio
async def test_teacher_cannot_view_attempts_for_another_teachers_assessment(api_client, db_session_factory):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)

    token = await login(api_client, seed.teacher.email)
    response = await api_client.get(
        f"/api/v1/teacher/assessments/{seed.other_assessment.id}/attempts",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_INSUFFICIENT_PERMISSIONS"


@pytest.mark.asyncio
async def test_teacher_cannot_grade_another_teachers_attempt(api_client, db_session_factory):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)

    token = await login(api_client, seed.teacher.email)
    response = await api_client.patch(
        f"/api/v1/teacher/attempts/{seed.other_attempt.id}/grade",
        headers={"Authorization": f"Bearer {token}"},
        json={"grades": [{"question_id": str(seed.other_question.id), "score_awarded": 0}]},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_INSUFFICIENT_PERMISSIONS"


@pytest.mark.asyncio
async def test_teacher_cannot_modify_another_teachers_assessment(api_client, db_session_factory):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)

    token = await login(api_client, seed.teacher.email)
    response = await api_client.patch(
        f"/api/v1/teacher/assessments/{seed.other_assessment.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Should not update"},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_INSUFFICIENT_PERMISSIONS"


@pytest.mark.asyncio
async def test_admin_can_access_cross_group_analytics(api_client, db_session_factory):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)

    token = await login(api_client, seed.admin.email)
    response = await api_client.get(
        f"/api/v1/teacher/groups/{seed.other_group.id}/analytics",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["group_id"] == str(seed.other_group.id)


@pytest.mark.asyncio
async def test_teacher_can_grade_own_attempt(api_client, db_session_factory):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)
        attempt = await create_attempt(db, assessment_id=seed.assessment.id, student_id=seed.student.id)
        answer = StudentAnswer(attempt_id=attempt.id, question_id=seed.question.id, answer_text="manual")
        db.add(answer)
        await db.commit()

    token = await login(api_client, seed.teacher.email)
    response = await api_client.patch(
        f"/api/v1/teacher/attempts/{attempt.id}/grade",
        headers={"Authorization": f"Bearer {token}"},
        json={"grades": [{"question_id": str(seed.question.id), "score_awarded": 7}]},
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "graded"
