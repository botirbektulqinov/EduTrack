"""
Create or update the initial EduTrack admin user.

Required environment variables:
    ADMIN_EMAIL
    ADMIN_PASSWORD

Optional:
    ADMIN_FULL_NAME
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401 - register ORM models
from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.security import hash_password
from app.models.user import User


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Set {name} before running scripts/create_admin.py.")
    return value


async def create_admin() -> None:
    email = required_env("ADMIN_EMAIL").strip().lower()
    password = required_env("ADMIN_PASSWORD")
    full_name = os.getenv("ADMIN_FULL_NAME", "System Administrator").strip()

    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            user.full_name = full_name
            user.role = "admin"
            user.password_hash = hash_password(password)
            user.is_active = True
            action = "updated"
        else:
            user = User(
                email=email,
                password_hash=hash_password(password),
                full_name=full_name,
                role="admin",
                is_active=True,
                extra_time_factor=1.0,
            )
            session.add(user)
            action = "created"

        await session.commit()

    print(f"Admin user {action}: {email}")


if __name__ == "__main__":
    asyncio.run(create_admin())
