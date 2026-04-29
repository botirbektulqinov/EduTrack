import pytest

from app.core.config import settings
from app.core.rate_limit import rate_limiter
from app.core import rate_limit as rate_limit_module
from tests.integration.factories import PASSWORD, seed_core_data

pytestmark = pytest.mark.integration


class FailingRedis:
    async def incr(self, _key):
        raise RuntimeError("force in-memory rate limiter")


@pytest.mark.asyncio
async def test_login_rate_limit_returns_429(api_client, db_session_factory, monkeypatch):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)

    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_LOGIN_PER_MINUTE", 2)
    monkeypatch.setattr(rate_limit_module, "redis_client", FailingRedis())
    rate_limiter.reset_memory()

    headers = {"X-Forwarded-For": "203.0.113.10"}
    payload = {"email": seed.student.email, "password": "wrong"}
    first = await api_client.post("/api/v1/auth/login", json=payload, headers=headers)
    second = await api_client.post("/api/v1/auth/login", json=payload, headers=headers)
    third = await api_client.post("/api/v1/auth/login", json=payload, headers=headers)

    assert first.status_code == 401
    assert second.status_code == 401
    assert third.status_code == 429
    assert third.json()["code"] == "RATE_LIMIT_EXCEEDED"


@pytest.mark.asyncio
async def test_assessment_start_rate_limit_returns_429(api_client, db_session_factory, monkeypatch):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)

    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": seed.student.email, "password": PASSWORD},
    )
    token = login.json()["access_token"]

    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_ASSESSMENT_START_PER_MINUTE", 1)
    monkeypatch.setattr(rate_limit_module, "redis_client", FailingRedis())
    rate_limiter.reset_memory()

    first = await api_client.post(
        f"/api/v1/student/take/{seed.assessment.access_token}/start",
        headers={"Authorization": f"Bearer {token}"},
    )
    second = await api_client.post(
        f"/api/v1/student/take/{seed.assessment.access_token}/start",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["code"] == "RATE_LIMIT_EXCEEDED"
