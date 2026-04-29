import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment
from app.models.assessment_attempt import AssessmentAttempt
from app.models.group import Group
from app.models.group_enrollment import GroupEnrollment
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.student_answer import StudentAnswer
from app.models.subject import Subject
from app.models.user import User


PASSWORD = "Password123!"
PASSWORD_HASH = "$2b$12$bwc/He/FGACWmeGr.baak.lZERGn48M8ZgDTMenZdQglCQf1uZ3My"


async def seed_core_data(db: AsyncSession) -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    admin = User(
        email="admin@example.edu",
        password_hash=PASSWORD_HASH,
        full_name="Admin User",
        role="admin",
    )
    teacher = User(
        email="teacher@example.edu",
        password_hash=PASSWORD_HASH,
        full_name="Teacher One",
        role="teacher",
    )
    other_teacher = User(
        email="other.teacher@example.edu",
        password_hash=PASSWORD_HASH,
        full_name="Teacher Two",
        role="teacher",
    )
    student = User(
        email="student@example.edu",
        password_hash=PASSWORD_HASH,
        full_name="Student One",
        role="student",
        student_id_number="S001",
    )
    other_student = User(
        email="other.student@example.edu",
        password_hash=PASSWORD_HASH,
        full_name="Student Two",
        role="student",
        student_id_number="S002",
    )
    subject = Subject(name="Algorithms", code="CS201")
    db.add_all([admin, teacher, other_teacher, student, other_student, subject])
    await db.flush()

    group = Group(
        name="CS201-A",
        subject="Algorithms",
        subject_id=subject.id,
        academic_year="2026",
        semester="Spring",
        teacher_id=teacher.id,
    )
    other_group = Group(
        name="CS201-B",
        subject="Algorithms",
        subject_id=subject.id,
        academic_year="2026",
        semester="Spring",
        teacher_id=other_teacher.id,
    )
    db.add_all([group, other_group])
    await db.flush()

    db.add_all([
        GroupEnrollment(group_id=group.id, student_id=student.id),
        GroupEnrollment(group_id=other_group.id, student_id=other_student.id),
    ])

    assessment = Assessment(
        title="Published Quiz",
        description="Integration test quiz",
        assessment_type="quiz",
        format_type="standard",
        group_id=group.id,
        subject_id=subject.id,
        teacher_id=teacher.id,
        time_limit_minutes=30,
        available_from=now - timedelta(hours=1),
        available_until=now + timedelta(hours=1),
        max_attempts=1,
        passing_score=50,
        total_points=10,
        is_published=True,
        is_active=True,
        max_violations=3,
        time_penalty_minutes=2,
    )
    other_assessment = Assessment(
        title="Other Teacher Quiz",
        assessment_type="quiz",
        format_type="standard",
        group_id=other_group.id,
        subject_id=subject.id,
        teacher_id=other_teacher.id,
        time_limit_minutes=30,
        available_from=now - timedelta(hours=1),
        available_until=now + timedelta(hours=1),
        max_attempts=1,
        passing_score=50,
        total_points=10,
        is_published=True,
        is_active=True,
    )
    db.add_all([assessment, other_assessment])
    await db.flush()

    correct_option = QuestionOption(content="4", is_correct=True)
    wrong_option = QuestionOption(content="5", is_correct=False)
    question = Question(
        assessment_id=assessment.id,
        question_type="mcq_single",
        content="2 + 2 = ?",
        points=10,
        options=[correct_option, wrong_option],
    )
    other_question = Question(
        assessment_id=other_assessment.id,
        question_type="mcq_single",
        content="3 + 3 = ?",
        points=10,
        options=[QuestionOption(content="6", is_correct=True)],
    )
    db.add_all([question, other_question])
    await db.flush()

    other_attempt = AssessmentAttempt(
        assessment_id=other_assessment.id,
        student_id=other_student.id,
        status="graded",
        submitted_at=now,
        time_limit_seconds=1800,
        time_remaining_seconds=1200,
        score_raw=10,
        score_percent=100,
        grade="A",
    )
    db.add(other_attempt)
    await db.flush()
    db.add(
        StudentAnswer(
            attempt_id=other_attempt.id,
            question_id=other_question.id,
            selected_option_ids=[other_question.options[0].id],
            score_awarded=10,
            auto_graded=True,
        )
    )

    await db.commit()
    return SimpleNamespace(
        password=PASSWORD,
        admin=admin,
        teacher=teacher,
        other_teacher=other_teacher,
        student=student,
        other_student=other_student,
        subject=subject,
        group=group,
        other_group=other_group,
        assessment=assessment,
        other_assessment=other_assessment,
        question=question,
        correct_option=correct_option,
        wrong_option=wrong_option,
        other_question=other_question,
        other_attempt=other_attempt,
    )


async def create_assessment_for_window(
    db: AsyncSession,
    seed: SimpleNamespace,
    *,
    available_from: datetime | None,
    available_until: datetime | None,
) -> Assessment:
    assessment = Assessment(
        title=f"Window Quiz {uuid.uuid4()}",
        assessment_type="quiz",
        format_type="standard",
        group_id=seed.group.id,
        subject_id=seed.subject.id,
        teacher_id=seed.teacher.id,
        time_limit_minutes=30,
        available_from=available_from,
        available_until=available_until,
        max_attempts=1,
        passing_score=50,
        total_points=1,
        is_published=True,
        is_active=True,
    )
    db.add(assessment)
    await db.flush()
    db.add(
        Question(
            assessment_id=assessment.id,
            question_type="mcq_single",
            content="Window question",
            points=1,
            options=[QuestionOption(content="Yes", is_correct=True)],
        )
    )
    await db.commit()
    return assessment


async def create_attempt(
    db: AsyncSession,
    *,
    assessment_id,
    student_id,
    status: str = "in_progress",
) -> AssessmentAttempt:
    attempt = AssessmentAttempt(
        assessment_id=assessment_id,
        student_id=student_id,
        status=status,
        time_limit_seconds=1800,
        time_remaining_seconds=1800,
    )
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)
    return attempt
