import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from starlette.testclient import TestClient

import app.models  # noqa: F401 - ensure all ORM models are registered
from app.api.v1 import auth as auth_api
from app.api.websocket import proctoring as proctoring_ws
from app.core import rate_limit as rate_limit_module
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.rate_limit import rate_limiter
from app.main import app
from app.services import password_reset_service


RUN_DB_TESTS = os.getenv("EDUTRACK_RUN_DB_TESTS") == "1"
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
TEST_REDIS_URL = os.getenv("TEST_REDIS_URL") or os.getenv("REDIS_URL")


@pytest_asyncio.fixture
async def db_engine():
    if not RUN_DB_TESTS:
        pytest.skip("Set EDUTRACK_RUN_DB_TESTS=1 to run PostgreSQL integration tests.")
    if not TEST_DATABASE_URL:
        pytest.skip("Set TEST_DATABASE_URL to an isolated PostgreSQL database.")

    engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True, poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        await engine.dispose()
        pytest.fail(f"Could not connect to TEST_DATABASE_URL: {exc}")

    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session_factory(db_engine):
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    try:
        yield session_factory
    finally:
        async with db_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def api_client(db_session_factory, monkeypatch) -> AsyncGenerator[AsyncClient, None]:
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    rate_limiter.reset_memory()

    async def override_get_db():
        async with db_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def ws_client(db_session_factory, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    rate_limiter.reset_memory()

    async def override_get_db():
        async with db_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(proctoring_ws, "async_session_factory", db_session_factory)
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def redis_test_client(monkeypatch):
    if not TEST_REDIS_URL:
        pytest.skip("Set TEST_REDIS_URL or REDIS_URL to run Redis-backed integration tests.")

    import redis.asyncio as aioredis

    client = aioredis.from_url(TEST_REDIS_URL, decode_responses=True)
    try:
        await client.ping()
    except Exception as exc:
        await client.aclose()
        pytest.skip(f"Redis is not reachable for integration tests: {exc}")

    await client.flushdb()
    monkeypatch.setattr(auth_api, "redis_client", client)
    monkeypatch.setattr(password_reset_service, "redis_client", client)
    monkeypatch.setattr(rate_limit_module, "redis_client", client)
    try:
        yield client
    finally:
        await client.flushdb()
        await client.aclose()
