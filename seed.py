"""
EduTrack — Seed Script
Creates default admin, teacher, and student accounts.

Usage:
    py seed.py
"""

import asyncio
import uuid
from datetime import datetime, timezone

import bcrypt
from sqlalchemy import select

from app.core.database import Base, async_session_factory, engine
from app.models import User


def hash_password(password: str) -> str:
    """Hash password with bcrypt (avoids passlib compat issues on 3.14)."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


SEED_USERS = [
    {
        "email": "admin@edutrack.edu",
        "password": "Admin123!",
        "full_name": "System Administrator",
        "role": "admin",
    },
    {
        "email": "teacher@edutrack.edu",
        "password": "Teacher123!",
        "full_name": "Demo Teacher",
        "role": "teacher",
        "employee_id": "EMP-001",
    },
    {
        "email": "student@edutrack.edu",
        "password": "Student123!",
        "full_name": "Demo Student",
        "role": "student",
        "student_id_number": "STU-001",
    },
]


async def seed() -> None:
    # Ensure tables exist (safe if already created via Alembic)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        for user_data in SEED_USERS:
            password = user_data.pop("password")

            # Skip if user already exists
            result = await session.execute(
                select(User).where(User.email == user_data["email"])
            )
            existing = result.scalar_one_or_none()
            if existing:
                print(f"  ✓ {user_data['email']} already exists — skipped")
                continue

            user = User(
                id=uuid.uuid4(),
                password_hash=hash_password(password),
                is_active=True,
                extra_time_factor=1.0,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                **user_data,
            )
            session.add(user)
            print(
                f"  + Created {user_data['role']:>8}  {user_data['email']}  /  {password}"
            )

        await session.commit()

    print("\nSeed complete.")


if __name__ == "__main__":
    print("Seeding EduTrack database...\n")
    asyncio.run(seed())
