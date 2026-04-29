from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from jose import jwt

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.services.password_reset_service import PasswordResetService
from tests.integration.factories import PASSWORD, seed_core_data

pytestmark = pytest.mark.integration


async def login_response(client, email: str, password: str = PASSWORD):
    return await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )


@pytest.mark.asyncio
async def test_access_token_accepted_on_protected_route(api_client, db_session_factory):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)

    login = await login_response(api_client, seed.student.email)
    token = login.json()["access_token"]
    response = await api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == seed.student.email


@pytest.mark.asyncio
async def test_refresh_token_rejected_where_access_token_required(api_client, db_session_factory):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)

    refresh = create_refresh_token(str(seed.student.id))
    response = await api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refresh}"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_TOKEN_EXPIRED"


@pytest.mark.asyncio
async def test_expired_access_token_rejected(api_client, db_session_factory):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)

    now = datetime.now(timezone.utc)
    expired = jwt.encode(
        {
            "sub": str(seed.student.id),
            "role": "student",
            "type": "access",
            "exp": now - timedelta(minutes=1),
            "iat": now - timedelta(minutes=5),
            "jti": str(uuid4()),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    response = await api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired}"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_TOKEN_EXPIRED"


@pytest.mark.asyncio
async def test_logout_blacklists_refresh_token_when_redis_available(
    api_client,
    db_session_factory,
    redis_test_client,
):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)

    login = await login_response(api_client, seed.student.email)
    access_token = login.json()["access_token"]
    refresh_token = login.json()["refresh_token"]
    logout = await api_client.post(
        "/api/v1/auth/logout",
        params={"refresh_token": refresh_token},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    refresh_after_logout = await api_client.post(
        "/api/v1/auth/refresh",
        params={"refresh_token": refresh_token},
    )

    assert logout.status_code == 200
    assert refresh_after_logout.status_code == 401
    assert refresh_after_logout.json()["code"] == "AUTH_TOKEN_EXPIRED"


@pytest.mark.asyncio
async def test_refresh_rotation_revokes_old_refresh_token_and_allows_new_one(
    api_client,
    db_session_factory,
    redis_test_client,
):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)

    login = await login_response(api_client, seed.student.email)
    old_refresh = login.json()["refresh_token"]
    first_refresh = await api_client.post(
        "/api/v1/auth/refresh",
        params={"refresh_token": old_refresh},
    )
    new_refresh = first_refresh.json()["refresh_token"]
    old_reuse = await api_client.post(
        "/api/v1/auth/refresh",
        params={"refresh_token": old_refresh},
    )
    new_reuse = await api_client.post(
        "/api/v1/auth/refresh",
        params={"refresh_token": new_refresh},
    )

    assert first_refresh.status_code == 200
    assert old_reuse.status_code == 401
    assert old_reuse.json()["code"] == "AUTH_TOKEN_EXPIRED"
    assert new_reuse.status_code == 200


@pytest.mark.asyncio
async def test_reset_token_is_one_time_use_when_redis_available(db_session_factory, redis_test_client):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)
        token = await PasswordResetService.issue_reset_token(seed.student)

    first = await PasswordResetService.consume_token(token)
    second = await PasswordResetService.consume_token(token)

    assert first == seed.student.id
    assert second is None


@pytest.mark.asyncio
async def test_signed_reset_fallback_is_disabled_unless_explicitly_allowed(
    db_session_factory,
    monkeypatch,
):
    class FailingRedis:
        async def setex(self, *_args):
            raise RuntimeError("redis unavailable")

        async def get(self, *_args):
            raise RuntimeError("redis unavailable")

    async with db_session_factory() as db:
        seed = await seed_core_data(db)

    monkeypatch.setattr("app.services.password_reset_service.redis_client", FailingRedis())
    monkeypatch.setattr(settings, "ALLOW_PASSWORD_RESET_SIGNED_FALLBACK", False)

    with pytest.raises(RuntimeError):
        await PasswordResetService.issue_reset_token(seed.student)

    assert await PasswordResetService.consume_token("not-a-real-token") is None


@pytest.mark.asyncio
async def test_forgot_password_does_not_reveal_email_existence(
    api_client,
    db_session_factory,
    monkeypatch,
):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)

    async def noop_send(_user):
        return None

    monkeypatch.setattr(PasswordResetService, "send_reset_instructions", noop_send)
    existing = await api_client.post("/api/v1/auth/forgot-password", json={"email": seed.student.email})
    missing = await api_client.post("/api/v1/auth/forgot-password", json={"email": "missing@example.edu"})

    assert existing.status_code == 200
    assert missing.status_code == 200
    assert existing.json() == missing.json()


@pytest.mark.asyncio
async def test_wrong_token_type_rejected_on_refresh(api_client, db_session_factory):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)

    access = create_access_token(str(seed.student.id), "student")
    response = await api_client.post("/api/v1/auth/refresh", params={"refresh_token": access})

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_TOKEN_EXPIRED"
