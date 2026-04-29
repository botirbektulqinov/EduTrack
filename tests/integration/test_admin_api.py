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
async def test_admin_can_list_users(api_client, db_session_factory):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)

    token = await login(api_client, seed.admin.email)
    response = await api_client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["meta"]["total"] >= 5


@pytest.mark.asyncio
@pytest.mark.parametrize("role_email", ["student@example.edu", "teacher@example.edu"])
async def test_non_admin_cannot_list_users(api_client, db_session_factory, role_email):
    async with db_session_factory() as db:
        await seed_core_data(db)

    token = await login(api_client, role_email)
    response = await api_client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_INSUFFICIENT_PERMISSIONS"


@pytest.mark.asyncio
async def test_admin_can_create_group(api_client, db_session_factory):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)

    token = await login(api_client, seed.admin.email)
    response = await api_client.post(
        "/api/v1/admin/groups",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "CS301-C",
            "subject": "Algorithms",
            "subject_id": str(seed.subject.id),
            "academic_year": "2026",
            "semester": "Fall",
            "teacher_id": str(seed.teacher.id),
        },
    )

    assert response.status_code == 201
    assert response.json()["data"]["name"] == "CS301-C"


@pytest.mark.asyncio
async def test_teacher_cannot_create_admin_group(api_client, db_session_factory):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)

    token = await login(api_client, seed.teacher.email)
    response = await api_client.post(
        "/api/v1/admin/groups",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Forbidden Group",
            "subject": "Algorithms",
            "academic_year": "2026",
            "semester": "Fall",
            "teacher_id": str(seed.teacher.id),
        },
    )

    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_INSUFFICIENT_PERMISSIONS"


@pytest.mark.asyncio
async def test_admin_deactivation_prevents_user_login(api_client, db_session_factory):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)

    admin_token = await login(api_client, seed.admin.email)
    deactivate = await api_client.delete(
        f"/api/v1/admin/users/{seed.student.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    login_after_deactivate = await api_client.post(
        "/api/v1/auth/login",
        json={"email": seed.student.email, "password": PASSWORD},
    )

    assert deactivate.status_code == 200
    assert login_after_deactivate.status_code == 401
    assert login_after_deactivate.json()["code"] == "AUTH_INVALID_CREDENTIALS"
