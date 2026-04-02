"""
EduTrack — Assessment Service
Assessment lifecycle management.
"""

import random
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment import Assessment
from app.models.curriculum_module import CurriculumModule
from app.models.group import Group
from app.models.question import Question
from app.models.subject import Subject
from app.models.topic import Topic
from app.models.assessment_attempt import AssessmentAttempt
from app.models.group_enrollment import GroupEnrollment
from app.schemas.assessment import AssessmentCreate, AssessmentUpdate


class AssessmentService:

    @staticmethod
    async def _resolve_subject_context(
        db: AsyncSession,
        teacher_id: UUID,
        group_id: UUID | None,
        subject_id: UUID | None,
    ) -> tuple[Group | None, UUID]:
        group = None
        subject = None

        if group_id:
            group = (
                await db.execute(
                    select(Group)
                    .options(selectinload(Group.curriculum_subject))
                    .where(Group.id == group_id)
                )
            ).scalar_one_or_none()
            if not group:
                raise HTTPException(
                    status_code=404,
                    detail={"code": "GROUP_NOT_FOUND", "message": "Group not found."},
                )
            if group.teacher_id != teacher_id:
                raise HTTPException(
                    status_code=403,
                    detail={"code": "AUTH_INSUFFICIENT_PERMISSIONS", "message": "Not your group."},
                )

        if subject_id:
            subject = await db.get(Subject, subject_id)
            if not subject:
                raise HTTPException(
                    status_code=404,
                    detail={"code": "SUBJECT_NOT_FOUND", "message": "Subject not found."},
                )

        if group and group.subject_id:
            if subject and subject.id != group.subject_id:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "ASSESSMENT_SUBJECT_GROUP_MISMATCH",
                        "message": "Selected subject must match the mapped subject of the selected group.",
                    },
                )
            subject_id = group.subject_id
        elif subject:
            subject_id = subject.id

        if not subject_id:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "ASSESSMENT_SUBJECT_REQUIRED",
                    "message": "Assessment must be linked to a curriculum subject.",
                },
            )

        return group, subject_id

    @staticmethod
    async def create_assessment(db: AsyncSession, teacher_id: UUID, data: AssessmentCreate) -> Assessment:
        """Create a new assessment in DRAFT state."""
        _, subject_id = await AssessmentService._resolve_subject_context(
            db,
            teacher_id,
            data.group_id,
            data.subject_id,
        )
        assessment = Assessment(
            title=data.title,
            description=data.description,
            assessment_type=data.assessment_type,
            format_type=data.format_type,
            group_id=data.group_id,
            subject_id=subject_id,
            teacher_id=teacher_id,
            time_limit_minutes=data.time_limit_minutes,
            available_from=data.available_from,
            available_until=data.available_until,
            max_attempts=data.max_attempts,
            scoring_policy=data.scoring_policy,
            passing_score=data.passing_score,
            score_release_policy=data.score_release_policy,
            shuffle_questions=data.shuffle_questions,
            shuffle_options=data.shuffle_options,
            password_protected=data.password_protected,
            # Proctoring
            enforce_fullscreen=data.proctoring.enforce_fullscreen,
            max_violations=data.proctoring.max_violations,
            time_penalty_minutes=data.proctoring.time_penalty_minutes,
            block_keyboard_shortcuts=data.proctoring.block_keyboard_shortcuts,
            tab_switch_detection=data.proctoring.tab_switch_detection,
            devtools_detection=data.proctoring.devtools_detection,
            right_click_block=data.proctoring.right_click_block,
            copy_paste_block=data.proctoring.copy_paste_block,
            webcam_proctoring=data.proctoring.webcam_proctoring,
            is_published=False,
        )
        if data.access_password:
            from app.core.security import hash_password
            assessment.access_password_hash = hash_password(data.access_password)

        db.add(assessment)
        await db.flush()
        await db.refresh(assessment)
        return assessment

    @staticmethod
    async def get_assessment(db: AsyncSession, assessment_id: UUID) -> Optional[Assessment]:
        result = await db.execute(
            select(Assessment)
            .options(
                selectinload(Assessment.questions).selectinload(Question.options),
                selectinload(Assessment.questions).selectinload(Question.topic).selectinload(Topic.module).selectinload(CurriculumModule.subject),
                selectinload(Assessment.curriculum_subject),
                selectinload(Assessment.group).selectinload(Group.curriculum_subject),
            )
            .where(Assessment.id == assessment_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_assessment_by_token(db: AsyncSession, token: UUID) -> Optional[Assessment]:
        result = await db.execute(
            select(Assessment)
            .options(
                selectinload(Assessment.questions).selectinload(Question.options),
                selectinload(Assessment.questions).selectinload(Question.topic).selectinload(Topic.module).selectinload(CurriculumModule.subject),
                selectinload(Assessment.curriculum_subject),
                selectinload(Assessment.group).selectinload(Group.curriculum_subject),
            )
            .where(Assessment.access_token == token)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_teacher_assessments(
        db: AsyncSession,
        teacher_id: UUID,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[List[Assessment], int]:
        query = (
            select(Assessment)
            .options(
                selectinload(Assessment.curriculum_subject),
                selectinload(Assessment.group).selectinload(Group.curriculum_subject),
                selectinload(Assessment.questions).selectinload(Question.options),
                selectinload(Assessment.questions).selectinload(Question.topic).selectinload(Topic.module).selectinload(CurriculumModule.subject),
            )
            .where(Assessment.teacher_id == teacher_id)
        )
        count_query = select(func.count(Assessment.id)).where(Assessment.teacher_id == teacher_id)

        total: int = (await db.execute(count_query)).scalar() or 0
        query = query.order_by(Assessment.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await db.execute(query)
        return list(result.scalars().all()), total

    @staticmethod
    async def update_assessment(db: AsyncSession, assessment: Assessment, data: AssessmentUpdate) -> Assessment:
        update_data = data.model_dump(exclude_unset=True)
        proctoring = update_data.pop("proctoring", None)
        next_group_id = update_data.pop("group_id", assessment.group_id)
        next_subject_id = update_data.pop("subject_id", assessment.subject_id)
        _, resolved_subject_id = await AssessmentService._resolve_subject_context(
            db,
            assessment.teacher_id,
            next_group_id,
            next_subject_id,
        )
        assessment.group_id = next_group_id
        assessment.subject_id = resolved_subject_id
        for field, value in update_data.items():
            setattr(assessment, field, value)
        if proctoring:
            for field, value in proctoring.items():
                setattr(assessment, field, value)
        await db.flush()
        await db.refresh(assessment)
        return assessment

    @staticmethod
    async def publish_assessment(db: AsyncSession, assessment: Assessment) -> Assessment:
        """Publish — generate access token, make available."""
        assessment.is_published = True
        assessment.is_active = True
        # Recalculate total points
        result = await db.execute(
            select(func.sum(Question.points))
            .where(Question.assessment_id == assessment.id)
        )
        total = result.scalar() or 0.0
        assessment.total_points = total
        await db.flush()
        await db.refresh(assessment)
        return assessment

    @staticmethod
    async def unpublish_assessment(db: AsyncSession, assessment: Assessment) -> Assessment:
        assessment.is_published = False
        await db.flush()
        return assessment

    @staticmethod
    async def deactivate_assessment(db: AsyncSession, assessment: Assessment) -> Assessment:
        """Immediately invalidate the access link."""
        assessment.is_active = False
        await db.flush()
        return assessment

    @staticmethod
    async def delete_assessment(db: AsyncSession, assessment: Assessment) -> None:
        await db.delete(assessment)
        await db.flush()

    @staticmethod
    async def validate_student_access(
        db: AsyncSession,
        assessment: Assessment,
        student_id: UUID,
    ) -> tuple[bool, str]:
        """Validate whether a student can access this assessment. Returns (ok, reason)."""
        if not assessment.is_published:
            return False, "ASSESSMENT_NOT_PUBLISHED"
        if not assessment.is_active:
            return False, "ASSESSMENT_DEACTIVATED"

        now = datetime.now(timezone.utc)
        if assessment.available_from and now < assessment.available_from:
            return False, "ASSESSMENT_NOT_YET_AVAILABLE"
        if assessment.available_until and now > assessment.available_until:
            return False, "ASSESSMENT_EXPIRED"

        # Check enrollment
        if assessment.group_id:
            enrollment = await db.execute(
                select(GroupEnrollment).where(
                    GroupEnrollment.group_id == assessment.group_id,
                    GroupEnrollment.student_id == student_id,
                )
            )
            if not enrollment.scalar_one_or_none():
                return False, "STUDENT_NOT_IN_GROUP"

        # Check attempt count
        attempt_count: int = (await db.execute(
            select(func.count(AssessmentAttempt.id)).where(
                AssessmentAttempt.assessment_id == assessment.id,
                AssessmentAttempt.student_id == student_id,
            )
        )).scalar() or 0

        if attempt_count >= assessment.max_attempts:
            return False, "ASSESSMENT_MAX_ATTEMPTS"

        return True, "OK"

    @staticmethod
    def get_shuffled_questions(assessment: Assessment, seed: Optional[int] = None) -> list[Question]:
        """Return questions in shuffled order if configured."""
        questions = list(assessment.questions)
        if assessment.shuffle_questions:
            rng = random.Random(seed)
            rng.shuffle(questions)
        return questions
