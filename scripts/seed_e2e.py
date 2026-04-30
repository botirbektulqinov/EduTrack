"""
Deterministic EduTrack E2E seed data.

This script is intentionally scoped to stable e2e@edutrack.test users and
E2E-named records. It refuses to run in production.
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401 - register ORM models
from sqlalchemy import delete, select, text

from app.core.config import settings
from app.core.database import async_session_factory, engine
from app.core.security import hash_password
from app.models.assessment import Assessment
from app.models.assessment_attempt import AssessmentAttempt
from app.models.curriculum_module import CurriculumModule
from app.models.group import Group
from app.models.group_enrollment import GroupEnrollment
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.student_answer import StudentAnswer
from app.models.subject import Subject
from app.models.topic import Topic
from app.models.user import User
from app.models.violation import Violation

ADMIN_EMAIL = "admin.e2e@edutrack.test"
TEACHER_EMAIL = "teacher.e2e@edutrack.test"
TEACHER2_EMAIL = "teacher2.e2e@edutrack.test"
STUDENT_EMAIL = "student.e2e@edutrack.test"
STUDENT2_EMAIL = "student2.e2e@edutrack.test"

PASSWORD = os.getenv("E2E_PASSWORD") or "E2EPassword123!"
SUBJECT_NAME = "E2E Assessment Engineering"
MODULE_NAME = "E2E Fundamentals"
TOPIC_NAME = "E2E Deterministic Quiz Topic"
GROUP_NAME = "E2E QA Group A"
OTHER_GROUP_NAME = "E2E QA Group B"
ACTIVE_ASSESSMENT_TITLE = "E2E Seeded Assessment"
ANALYTICS_ASSESSMENT_TITLE = "E2E Previous Analytics Quiz"
OTHER_ASSESSMENT_TITLE = "E2E Other Teacher Assessment"


def assert_safe_environment() -> None:
    if settings.ENVIRONMENT == "production":
        raise SystemExit("Refusing to seed E2E data when ENVIRONMENT=production.")

    parsed = urlparse(settings.DATABASE_URL.replace("+asyncpg", ""))
    db_name = (parsed.path or "").lstrip("/")
    host = parsed.hostname or ""
    safe_name = any(token in db_name.lower() for token in ("test", "e2e", "edu_track"))
    safe_host = host in {"localhost", "127.0.0.1", "postgres", ""}
    if not safe_name or not safe_host:
        raise SystemExit(
            f"Refusing to seed E2E data for DATABASE_URL host={host!r} db={db_name!r}."
        )


async def assert_migrations_applied() -> None:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                """
                SELECT
                  to_regclass('public.alembic_version') AS alembic_version,
                  to_regclass('public.users') AS users_table
                """
            )
        )
        row = result.one()

    if row.alembic_version is None or row.users_table is None:
        raise SystemExit("Run `alembic upgrade head` before `python scripts/seed_e2e.py`.")


async def get_or_create_user(session, *, email: str, full_name: str, role: str, **extra) -> User:
    user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
    password_hash = hash_password(PASSWORD)
    if user:
        user.full_name = full_name
        user.role = role
        user.password_hash = password_hash
        user.is_active = True
        user.extra_time_factor = 1.0
        for key, value in extra.items():
            setattr(user, key, value)
        return user

    user = User(
        email=email,
        full_name=full_name,
        role=role,
        password_hash=password_hash,
        is_active=True,
        extra_time_factor=1.0,
        **extra,
    )
    session.add(user)
    await session.flush()
    return user


async def get_or_create_subject(session) -> tuple[Subject, CurriculumModule, Topic]:
    subject = (await session.execute(select(Subject).where(Subject.name == SUBJECT_NAME))).scalar_one_or_none()
    if not subject:
        subject = Subject(name=SUBJECT_NAME, code="E2E-QA", description="Deterministic E2E subject")
        session.add(subject)
        await session.flush()

    module = (
        await session.execute(
            select(CurriculumModule).where(
                CurriculumModule.subject_id == subject.id,
                CurriculumModule.name == MODULE_NAME,
            )
        )
    ).scalar_one_or_none()
    if not module:
        module = CurriculumModule(subject_id=subject.id, name=MODULE_NAME, order_index=1)
        session.add(module)
        await session.flush()

    topic = (
        await session.execute(
            select(Topic).where(Topic.module_id == module.id, Topic.name == TOPIC_NAME)
        )
    ).scalar_one_or_none()
    if not topic:
        topic = Topic(module_id=module.id, name=TOPIC_NAME, order_index=1)
        session.add(topic)
        await session.flush()

    return subject, module, topic


async def get_or_create_group(session, *, name: str, teacher: User, subject: Subject) -> Group:
    group = (
        await session.execute(
            select(Group).where(Group.name == name, Group.teacher_id == teacher.id)
        )
    ).scalar_one_or_none()
    if group:
        group.subject = subject.name
        group.subject_id = subject.id
        group.academic_year = "2026"
        group.semester = "Spring"
        group.is_archived = False
        return group

    group = Group(
        name=name,
        subject=subject.name,
        subject_id=subject.id,
        academic_year="2026",
        semester="Spring",
        teacher_id=teacher.id,
        is_archived=False,
    )
    session.add(group)
    await session.flush()
    return group


async def ensure_enrollment(session, *, group: Group, student: User) -> None:
    enrollment = (
        await session.execute(
            select(GroupEnrollment).where(
                GroupEnrollment.group_id == group.id,
                GroupEnrollment.student_id == student.id,
            )
        )
    ).scalar_one_or_none()
    if not enrollment:
        session.add(GroupEnrollment(group_id=group.id, student_id=student.id))


async def reset_e2e_assessments(session) -> None:
    assessments = (
        await session.execute(
            select(Assessment.id).where(
                Assessment.title.in_([
                    ACTIVE_ASSESSMENT_TITLE,
                    ANALYTICS_ASSESSMENT_TITLE,
                    OTHER_ASSESSMENT_TITLE,
                ])
            )
        )
    ).scalars().all()
    if not assessments:
        return

    attempt_ids = (
        await session.execute(
            select(AssessmentAttempt.id).where(AssessmentAttempt.assessment_id.in_(assessments))
        )
    ).scalars().all()
    question_ids = (
        await session.execute(select(Question.id).where(Question.assessment_id.in_(assessments)))
    ).scalars().all()

    if attempt_ids:
        await session.execute(delete(Violation).where(Violation.attempt_id.in_(attempt_ids)))
        await session.execute(delete(StudentAnswer).where(StudentAnswer.attempt_id.in_(attempt_ids)))
        await session.execute(delete(AssessmentAttempt).where(AssessmentAttempt.id.in_(attempt_ids)))
    if question_ids:
        await session.execute(delete(QuestionOption).where(QuestionOption.question_id.in_(question_ids)))
        await session.execute(delete(Question).where(Question.id.in_(question_ids)))
    await session.execute(delete(Assessment).where(Assessment.id.in_(assessments)))
    await session.flush()


def add_option(session, question: Question, content: str, is_correct: bool = False) -> QuestionOption:
    option = QuestionOption(question_id=question.id, content=content, is_correct=is_correct)
    session.add(option)
    return option


async def create_active_assessment(session, *, teacher: User, group: Group, subject: Subject, topic: Topic) -> Assessment:
    now = datetime.now(timezone.utc)
    assessment = Assessment(
        title=ACTIVE_ASSESSMENT_TITLE,
        description="Deterministic assessment used by real Playwright E2E tests.",
        assessment_type="quiz",
        format_type="standard",
        group_id=group.id,
        subject_id=subject.id,
        teacher_id=teacher.id,
        time_limit_minutes=20,
        available_from=now - timedelta(days=1),
        available_until=now + timedelta(days=14),
        max_attempts=3,
        passing_score=60,
        total_points=3,
        score_release_policy="immediate",
        shuffle_questions=False,
        shuffle_options=False,
        enforce_fullscreen=False,
        max_violations=5,
        time_penalty_minutes=0,
        block_keyboard_shortcuts=False,
        tab_switch_detection=False,
        devtools_detection=False,
        right_click_block=False,
        copy_paste_block=False,
        is_published=True,
        is_active=True,
    )
    session.add(assessment)
    await session.flush()

    q1 = Question(
        assessment_id=assessment.id,
        question_type="mcq_single",
        content="E2E: Which answer is correct?",
        points=1,
        order_index=1,
        topic_id=topic.id,
        difficulty="easy",
    )
    q2 = Question(
        assessment_id=assessment.id,
        question_type="numeric",
        content="E2E: What is 6 * 7?",
        points=1,
        order_index=2,
        topic_id=topic.id,
        difficulty="easy",
        config={"correct_value": 42, "tolerance": 0, "unit": ""},
    )
    q3 = Question(
        assessment_id=assessment.id,
        question_type="short_answer",
        content="E2E: Briefly explain what a regression test protects.",
        points=1,
        order_index=3,
        topic_id=topic.id,
        difficulty="medium",
        config={"accepted_answers": []},
    )
    session.add_all([q1, q2, q3])
    await session.flush()
    add_option(session, q1, "Correct seeded option", True)
    add_option(session, q1, "Incorrect seeded option", False)
    return assessment


async def create_previous_analytics_attempt(
    session,
    *,
    teacher: User,
    student: User,
    group: Group,
    subject: Subject,
    topic: Topic,
) -> None:
    now = datetime.now(timezone.utc)
    assessment = Assessment(
        title=ANALYTICS_ASSESSMENT_TITLE,
        description="Previous completed quiz used by analytics E2E tests.",
        assessment_type="quiz",
        format_type="standard",
        group_id=group.id,
        subject_id=subject.id,
        teacher_id=teacher.id,
        time_limit_minutes=10,
        available_from=now - timedelta(days=7),
        available_until=now + timedelta(days=7),
        max_attempts=1,
        passing_score=60,
        total_points=1,
        score_release_policy="immediate",
        is_published=True,
        is_active=True,
        enforce_fullscreen=False,
    )
    session.add(assessment)
    await session.flush()

    question = Question(
        assessment_id=assessment.id,
        question_type="mcq_single",
        content="E2E previous analytics question",
        points=1,
        order_index=1,
        topic_id=topic.id,
    )
    session.add(question)
    await session.flush()
    option = add_option(session, question, "Correct", True)
    await session.flush()

    attempt = AssessmentAttempt(
        assessment_id=assessment.id,
        student_id=student.id,
        status="graded",
        started_at=now - timedelta(days=2, minutes=3),
        submitted_at=now - timedelta(days=2),
        time_limit_seconds=600,
        time_remaining_seconds=420,
        score_raw=1,
        score_percent=100,
        grade="A",
    )
    session.add(attempt)
    await session.flush()
    session.add(
        StudentAnswer(
            attempt_id=attempt.id,
            question_id=question.id,
            selected_option_ids=[option.id],
            score_awarded=1,
            auto_graded=True,
        )
    )


async def create_other_teacher_assessment(
    session,
    *,
    teacher: User,
    group: Group,
    subject: Subject,
) -> Assessment:
    now = datetime.now(timezone.utc)
    assessment = Assessment(
        title=OTHER_ASSESSMENT_TITLE,
        assessment_type="quiz",
        format_type="standard",
        group_id=group.id,
        subject_id=subject.id,
        teacher_id=teacher.id,
        time_limit_minutes=10,
        available_from=now - timedelta(days=1),
        available_until=now + timedelta(days=7),
        max_attempts=1,
        total_points=1,
        is_published=True,
        is_active=True,
    )
    session.add(assessment)
    await session.flush()
    question = Question(
        assessment_id=assessment.id,
        question_type="mcq_single",
        content="E2E other teacher question",
        points=1,
    )
    session.add(question)
    await session.flush()
    add_option(session, question, "Owned by teacher 2", True)
    return assessment


async def seed() -> None:
    assert_safe_environment()
    await assert_migrations_applied()

    async with async_session_factory() as session:
        admin = await get_or_create_user(
            session,
            email=ADMIN_EMAIL,
            full_name="E2E Admin",
            role="admin",
        )
        teacher = await get_or_create_user(
            session,
            email=TEACHER_EMAIL,
            full_name="E2E Teacher",
            role="teacher",
            employee_id="E2E-T001",
        )
        teacher2 = await get_or_create_user(
            session,
            email=TEACHER2_EMAIL,
            full_name="E2E Teacher Two",
            role="teacher",
            employee_id="E2E-T002",
        )
        student = await get_or_create_user(
            session,
            email=STUDENT_EMAIL,
            full_name="E2E Student",
            role="student",
            student_id_number="E2E-S001",
        )
        student2 = await get_or_create_user(
            session,
            email=STUDENT2_EMAIL,
            full_name="E2E Student Two",
            role="student",
            student_id_number="E2E-S002",
        )
        subject, _module, topic = await get_or_create_subject(session)
        group = await get_or_create_group(session, name=GROUP_NAME, teacher=teacher, subject=subject)
        other_group = await get_or_create_group(session, name=OTHER_GROUP_NAME, teacher=teacher2, subject=subject)
        await ensure_enrollment(session, group=group, student=student)
        await ensure_enrollment(session, group=other_group, student=student2)

        await reset_e2e_assessments(session)
        active = await create_active_assessment(
            session,
            teacher=teacher,
            group=group,
            subject=subject,
            topic=topic,
        )
        await create_previous_analytics_attempt(
            session,
            teacher=teacher,
            student=student,
            group=group,
            subject=subject,
            topic=topic,
        )
        other = await create_other_teacher_assessment(
            session,
            teacher=teacher2,
            group=other_group,
            subject=subject,
        )
        await session.commit()

    print("E2E seed complete.")
    print(f"  admin:    {admin.email}")
    print(f"  teacher:  {teacher.email}")
    print(f"  teacher2: {teacher2.email}")
    print(f"  student:  {student.email}")
    print(f"  student2: {student2.email}")
    print(f"  password: {PASSWORD}")
    print(f"  active_assessment_id: {active.id}")
    print(f"  active_assessment_token: {active.access_token}")
    print(f"  other_teacher_assessment_id: {other.id}")


if __name__ == "__main__":
    asyncio.run(seed())
