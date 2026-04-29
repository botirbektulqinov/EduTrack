import pytest

from tests.integration.factories import PASSWORD, seed_core_data

pytestmark = pytest.mark.integration


async def login(client, email: str, password: str = PASSWORD) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_login_success_and_invalid_credentials(api_client, db_session_factory):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)

    ok = await api_client.post(
        "/api/v1/auth/login",
        json={"email": seed.student.email, "password": PASSWORD},
    )
    bad = await api_client.post(
        "/api/v1/auth/login",
        json={"email": seed.student.email, "password": "wrong"},
    )

    assert ok.status_code == 200
    assert ok.json()["token_type"] == "bearer"
    assert bad.status_code == 401
    assert bad.json()["code"] == "AUTH_INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_teacher_cannot_access_another_teachers_group(api_client, db_session_factory):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)

    token = await login(api_client, seed.other_teacher.email)
    response = await api_client.get(
        f"/api/v1/teacher/groups/{seed.group.id}/analytics",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "GROUP_NOT_FOUND"


@pytest.mark.asyncio
async def test_student_cannot_access_another_students_result(api_client, db_session_factory):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)

    token = await login(api_client, seed.student.email)
    response = await api_client.get(
        f"/api/v1/student/results/{seed.other_attempt.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "ATTEMPT_NOT_FOUND"


@pytest.mark.asyncio
async def test_unauthorized_and_wrong_role_are_rejected(api_client, db_session_factory):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)

    unauthenticated = await api_client.get(f"/api/v1/teacher/groups/{seed.group.id}/analytics")
    student_token = await login(api_client, seed.student.email)
    wrong_role = await api_client.get(
        f"/api/v1/teacher/groups/{seed.group.id}/analytics",
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert unauthenticated.status_code == 401
    assert wrong_role.status_code == 403
    assert wrong_role.json()["code"] == "AUTH_INSUFFICIENT_PERMISSIONS"
