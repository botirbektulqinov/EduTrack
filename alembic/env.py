"""
Alembic environment for EduTrack.
"""

import asyncio
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

load_dotenv()

from app.core.config import settings  # noqa: E402
from app.core.database import Base  # noqa: E402

import app.models.assessment  # noqa: F401, E402
import app.models.assessment_attempt  # noqa: F401, E402
import app.models.audit_log  # noqa: F401, E402
import app.models.curriculum_module  # noqa: F401, E402
import app.models.department  # noqa: F401, E402
import app.models.group  # noqa: F401, E402
import app.models.group_enrollment  # noqa: F401, E402
import app.models.notification  # noqa: F401, E402
import app.models.performance_snapshot  # noqa: F401, E402
import app.models.question  # noqa: F401, E402
import app.models.question_bank  # noqa: F401, E402
import app.models.question_option  # noqa: F401, E402
import app.models.question_revision  # noqa: F401, E402
import app.models.student_answer  # noqa: F401, E402
import app.models.subject  # noqa: F401, E402
import app.models.topic  # noqa: F401, E402
import app.models.user  # noqa: F401, E402
import app.models.violation  # noqa: F401, E402

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in offline mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in online mode using an async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
