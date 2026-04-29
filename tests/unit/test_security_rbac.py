import uuid

import pytest
from fastapi import HTTPException

from app.api.deps import require_role
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.models.user import User


def user(role: str) -> User:
    return User(
        id=uuid.uuid4(),
        email=f"{role}@example.edu",
        password_hash="hash",
        full_name=f"{role.title()} User",
        role=role,
        is_active=True,
    )


@pytest.mark.asyncio
async def test_admin_role_dependency_accepts_admin():
    checker = require_role("admin")

    assert await checker(user("admin")) is not None


@pytest.mark.asyncio
async def test_admin_role_dependency_rejects_teacher_with_403():
    checker = require_role("admin")

    with pytest.raises(HTTPException) as exc:
        await checker(user("teacher"))

    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "AUTH_INSUFFICIENT_PERMISSIONS"


def test_access_and_refresh_tokens_have_distinct_types():
    user_id = str(uuid.uuid4())

    access_payload = decode_token(create_access_token(user_id, "student"))
    refresh_payload = decode_token(create_refresh_token(user_id))

    assert access_payload["sub"] == user_id
    assert access_payload["role"] == "student"
    assert access_payload["type"] == "access"
    assert refresh_payload["sub"] == user_id
    assert refresh_payload["type"] == "refresh"


def test_decode_token_rejects_invalid_token():
    assert decode_token("not-a-real-jwt") is None
