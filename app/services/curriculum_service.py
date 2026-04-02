"""
EduTrack - Curriculum Service
"""

import re
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment import Assessment
from app.models.curriculum_module import CurriculumModule
from app.models.group import Group
from app.models.question import Question
from app.models.subject import Subject
from app.models.topic import Topic


class CurriculumService:
    IMPORTED_MODULE_NAME = "Imported Topics"

    @staticmethod
    def normalize_label(value: Optional[str]) -> str:
        if not value:
            return ""
        normalized = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
        return re.sub(r"\s+", " ", normalized)

    @staticmethod
    def group_subject_name(group: Optional[Group]) -> Optional[str]:
        if not group:
            return None
        if getattr(group, "curriculum_subject", None):
            return group.curriculum_subject.name
        return group.subject or group.name

    @staticmethod
    def assessment_subject_id(assessment: Optional[Assessment]) -> Optional[UUID]:
        if not assessment:
            return None
        if getattr(assessment, "subject_id", None):
            return assessment.subject_id
        group = getattr(assessment, "group", None)
        if group and getattr(group, "subject_id", None):
            return group.subject_id
        return None

    @staticmethod
    def assessment_subject_name(assessment: Optional[Assessment]) -> Optional[str]:
        if not assessment:
            return None
        if getattr(assessment, "curriculum_subject", None):
            return assessment.curriculum_subject.name
        group = getattr(assessment, "group", None)
        return CurriculumService.group_subject_name(group)

    @staticmethod
    def question_topic_name(question: Question) -> Optional[str]:
        if getattr(question, "topic", None):
            return question.topic.name
        return question.topic_tag

    @staticmethod
    async def list_tree(db: AsyncSession) -> list[Subject]:
        result = await db.execute(
            select(Subject)
            .options(
                selectinload(Subject.modules).selectinload(CurriculumModule.topics),
            )
            .order_by(Subject.name)
        )
        return list(result.scalars().all())

    @staticmethod
    async def find_subject_by_name(db: AsyncSession, name: Optional[str]) -> Optional[Subject]:
        target = CurriculumService.normalize_label(name)
        if not target:
            return None

        subjects = await CurriculumService.list_flat_subjects(db)
        for subject in subjects:
            if CurriculumService.normalize_label(subject.name) == target:
                return subject
        return None

    @staticmethod
    async def list_flat_subjects(db: AsyncSession) -> list[Subject]:
        result = await db.execute(select(Subject).order_by(Subject.name))
        return list(result.scalars().all())

    @staticmethod
    async def list_flat_topics(db: AsyncSession) -> list[Topic]:
        result = await db.execute(
            select(Topic)
            .options(selectinload(Topic.module).selectinload(CurriculumModule.subject))
            .order_by(Topic.name)
        )
        return list(result.scalars().all())

    @staticmethod
    async def resolve_group_subject(
        db: AsyncSession,
        subject_id: Optional[UUID],
        legacy_subject: Optional[str],
    ) -> Optional[Subject]:
        if subject_id:
            return await db.get(Subject, subject_id)
        return await CurriculumService.find_subject_by_name(db, legacy_subject)

    @staticmethod
    async def find_topic_for_subject(
        db: AsyncSession,
        topic_name: Optional[str],
        subject_id: Optional[UUID],
    ) -> Optional[Topic]:
        normalized_topic = CurriculumService.normalize_label(topic_name)
        if not normalized_topic:
            return None

        topics = await CurriculumService.list_flat_topics(db)
        for topic in topics:
            if subject_id and topic.module.subject_id != subject_id:
                continue
            if CurriculumService.normalize_label(topic.name) == normalized_topic:
                return topic
        return None

    @staticmethod
    async def assign_group_subject(db: AsyncSession, group: Group, subject: Subject) -> Group:
        previous_subject_id = group.subject_id
        group.subject_id = subject.id
        group.subject = subject.name
        assessments_result = await db.execute(
            select(Assessment).where(Assessment.group_id == group.id)
        )
        assessments = assessments_result.scalars().all()
        for assessment in assessments:
            if assessment.subject_id is None or assessment.subject_id == previous_subject_id:
                assessment.subject_id = subject.id
        await db.flush()
        await db.refresh(group)
        return group

    @staticmethod
    async def assign_question_topic(db: AsyncSession, question: Question, topic: Topic) -> Question:
        question.topic_id = topic.id
        question.topic_tag = topic.name
        await db.flush()
        await db.refresh(question)
        return question

    @staticmethod
    async def ensure_imported_module(db: AsyncSession, subject_id: UUID) -> CurriculumModule:
        result = await db.execute(
            select(CurriculumModule)
            .where(
                CurriculumModule.subject_id == subject_id,
                CurriculumModule.name == CurriculumService.IMPORTED_MODULE_NAME,
            )
        )
        module = result.scalar_one_or_none()
        if module:
            return module

        module = CurriculumModule(
            subject_id=subject_id,
            name=CurriculumService.IMPORTED_MODULE_NAME,
            description="Auto-generated module for legacy topic mappings.",
            order_index=999,
        )
        db.add(module)
        await db.flush()
        return module

    @staticmethod
    async def ensure_topic_for_subject(
        db: AsyncSession,
        subject_id: UUID,
        topic_name: str,
    ) -> Topic:
        existing = await CurriculumService.find_topic_for_subject(db, topic_name, subject_id)
        if existing:
            return existing

        module = await CurriculumService.ensure_imported_module(db, subject_id)
        topic = Topic(module_id=module.id, name=topic_name.strip(), order_index=0)
        db.add(topic)
        await db.flush()
        return topic

    @staticmethod
    async def get_review_queue(db: AsyncSession) -> dict:
        subjects = await CurriculumService.list_flat_subjects(db)
        subject_lookup = {
            CurriculumService.normalize_label(subject.name): subject for subject in subjects
        }

        groups_result = await db.execute(
            select(Group)
            .options(selectinload(Group.curriculum_subject))
            .order_by(Group.name)
        )
        groups = groups_result.scalars().all()

        group_items = []
        for group in groups:
            if group.subject_id is not None:
                continue
            suggested = subject_lookup.get(CurriculumService.normalize_label(group.subject))
            group_items.append({
                "group_id": group.id,
                "group_name": group.name,
                "legacy_subject": group.subject,
                "current_subject_id": group.subject_id,
                "current_subject_name": group.curriculum_subject.name if group.curriculum_subject else None,
                "suggested_subject_id": suggested.id if suggested else None,
                "suggested_subject_name": suggested.name if suggested else None,
            })

        questions_result = await db.execute(
            select(Question)
            .options(
                selectinload(Question.topic).selectinload(Topic.module).selectinload(CurriculumModule.subject),
                selectinload(Question.assessment).selectinload(Assessment.group).selectinload(Group.curriculum_subject),
            )
            .where(Question.topic_tag.isnot(None))
            .order_by(Question.created_at.desc())
        )
        questions = questions_result.scalars().all()

        question_items = []
        for question in questions:
            if question.topic_id is not None:
                continue
            assessment = question.assessment
            group = assessment.group if assessment else None
            subject = assessment.curriculum_subject if assessment and assessment.curriculum_subject else (group.curriculum_subject if group else None)
            suggested = await CurriculumService.find_topic_for_subject(
                db,
                question.topic_tag,
                CurriculumService.assessment_subject_id(assessment),
            )
            question_items.append({
                "question_id": question.id,
                "assessment_id": assessment.id if assessment else None,
                "assessment_title": assessment.title if assessment else None,
                "content_preview": question.content[:120],
                "legacy_topic": question.topic_tag,
                "subject_id": subject.id if subject else None,
                "subject_name": CurriculumService.assessment_subject_name(assessment),
                "current_topic_id": question.topic_id,
                "current_topic_name": question.topic.name if question.topic else None,
                "suggested_topic_id": suggested.id if suggested else None,
                "suggested_topic_name": suggested.name if suggested else None,
            })

        return {
            "groups": group_items,
            "questions": question_items,
        }

    @staticmethod
    async def sync_legacy_data(db: AsyncSession) -> dict:
        created_subjects = 0
        created_topics = 0
        mapped_groups = 0
        mapped_assessments = 0
        mapped_questions = 0

        groups_result = await db.execute(
            select(Group).options(selectinload(Group.curriculum_subject))
        )
        groups = groups_result.scalars().all()

        for group in groups:
            if not group.subject:
                continue
            subject = await CurriculumService.find_subject_by_name(db, group.subject)
            if not subject:
                subject = Subject(name=group.subject.strip())
                db.add(subject)
                await db.flush()
                created_subjects += 1

            if group.subject_id is None:
                group.subject_id = subject.id
                group.subject = subject.name
                mapped_groups += 1

        assessments_result = await db.execute(
            select(Assessment)
            .options(
                selectinload(Assessment.curriculum_subject),
                selectinload(Assessment.group).selectinload(Group.curriculum_subject),
                selectinload(Assessment.questions).selectinload(Question.topic).selectinload(Topic.module),
            )
        )
        assessments = assessments_result.scalars().all()

        for assessment in assessments:
            if assessment.subject_id is not None:
                continue

            inferred_subject_id = None
            if assessment.group and assessment.group.subject_id:
                inferred_subject_id = assessment.group.subject_id
            elif assessment.questions:
                topic_subject_ids = {
                    question.topic.module.subject_id
                    for question in assessment.questions
                    if question.topic and question.topic.module and question.topic.module.subject_id
                }
                if len(topic_subject_ids) == 1:
                    inferred_subject_id = next(iter(topic_subject_ids))

            if inferred_subject_id:
                assessment.subject_id = inferred_subject_id
                mapped_assessments += 1

        questions_result = await db.execute(
            select(Question)
            .options(
                selectinload(Question.assessment).selectinload(Assessment.curriculum_subject),
                selectinload(Question.assessment).selectinload(Assessment.group).selectinload(Group.curriculum_subject),
            )
            .where(Question.topic_tag.isnot(None))
        )
        questions = questions_result.scalars().all()

        for question in questions:
            if question.topic_id is not None or not question.topic_tag:
                continue

            subject_id = None
            if question.assessment:
                assessment = question.assessment
                if assessment.curriculum_subject:
                    subject_id = assessment.curriculum_subject.id
                elif assessment.subject_id:
                    subject_id = assessment.subject_id
                elif assessment.group:
                    group = assessment.group
                    if group.curriculum_subject:
                        subject_id = group.curriculum_subject.id
                    elif group.subject_id:
                        subject_id = group.subject_id

            if not subject_id:
                continue

            existing = await CurriculumService.find_topic_for_subject(db, question.topic_tag, subject_id)
            if existing is None:
                existing = await CurriculumService.ensure_topic_for_subject(db, subject_id, question.topic_tag)
                created_topics += 1

            question.topic_id = existing.id
            question.topic_tag = existing.name
            mapped_questions += 1

        await db.flush()

        return {
            "created_subjects": created_subjects,
            "created_topics": created_topics,
            "mapped_groups": mapped_groups,
            "mapped_assessments": mapped_assessments,
            "mapped_questions": mapped_questions,
        }
