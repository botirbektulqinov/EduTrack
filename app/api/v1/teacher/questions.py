"""
EduTrack — Teacher: Question Management API
"""

from uuid import UUID

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_teacher_user
from app.models.user import User
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.assessment import Assessment
from app.models.curriculum_module import CurriculumModule
from app.models.group import Group
from app.models.topic import Topic
from app.models.question_revision import QuestionRevision
from app.schemas.question import (
    BulkQuestionCreate,
    QuestionCreate,
    QuestionResponse,
    QuestionUpdate,
    BulkQuestionImportRequest,
    BulkQuestionPreviewItem,
    BulkQuestionPreviewResponse,
    QuestionRevisionResponse,
)
from app.schemas.common import MessageResponse, SuccessResponse
from app.services.curriculum_service import CurriculumService
from app.services.question_revision_service import QuestionRevisionService

router = APIRouter(tags=["Teacher - Questions"])


def _serialize_question(question: Question) -> QuestionResponse:
    payload = QuestionResponse.model_validate(question)
    payload.topic_name = question.topic.name if question.topic else question.topic_tag
    payload.module_id = question.topic.module_id if question.topic and question.topic.module else None
    payload.module_name = question.topic.module.name if question.topic and question.topic.module else None
    payload.subject_id = (
        question.topic.module.subject_id
        if question.topic and question.topic.module
        else None
    )
    payload.subject_name = (
        question.topic.module.subject.name
        if question.topic and question.topic.module and question.topic.module.subject
        else None
    )
    return payload


def _serialize_revision(revision: QuestionRevision) -> QuestionRevisionResponse:
    return QuestionRevisionResponse.model_validate(revision)


def _extract_question_items(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("questions"), list):
        return payload["questions"]
    raise HTTPException(
        status_code=400,
        detail={
            "code": "INVALID_BULK_IMPORT_FORMAT",
            "message": 'Expected {"questions":[...]} or a raw array of question objects.',
        },
    )


def _get_code_case_counts(question_data: BulkQuestionCreate) -> tuple[int, int]:
    config = question_data.config or {}
    test_cases = config.get("test_cases") or []
    visible = sum(1 for item in test_cases if not item.get("is_hidden"))
    hidden = sum(1 for item in test_cases if item.get("is_hidden"))
    return visible, hidden


async def _resolve_topic(
    db: AsyncSession,
    topic_id: UUID | None,
    topic_tag: str | None,
    assessment: Assessment | None,
) -> Topic | None:
    if topic_id:
        topic = (
            await db.execute(
                select(Topic)
                .options(selectinload(Topic.module).selectinload(CurriculumModule.subject))
                .where(Topic.id == topic_id)
            )
        ).scalar_one_or_none()
        if not topic:
            raise HTTPException(
                status_code=404,
                detail={"code": "TOPIC_NOT_FOUND", "message": "Topic not found."},
            )

        assessment_subject_id = CurriculumService.assessment_subject_id(assessment)
        if assessment_subject_id:
            if topic.module.subject_id != assessment_subject_id:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "TOPIC_SUBJECT_MISMATCH",
                        "message": "Selected topic does not belong to the assessment subject.",
                    },
                )
        return topic

    subject_id = None
    if assessment:
        subject_id = CurriculumService.assessment_subject_id(assessment)
    if topic_tag:
        return await CurriculumService.find_topic_for_subject(db, topic_tag, subject_id)
    return None


async def _preview_question_item(
    db: AsyncSession,
    raw_question: Any,
    teacher: User,
    assessment_cache: dict[UUID, Assessment | None],
) -> BulkQuestionPreviewItem:
    warnings: list[str] = []
    errors: list[str] = []

    try:
        question_data = BulkQuestionCreate.model_validate(raw_question)
    except ValidationError as exc:
        error_messages = []
        for error in exc.errors():
            location = ".".join(str(part) for part in error.get("loc", []))
            error_messages.append(f"{location}: {error.get('msg')}")
        return BulkQuestionPreviewItem(
            index=0,
            is_valid=False,
            errors=error_messages,
        )

    assessment = None
    if question_data.assessment_id:
        if question_data.assessment_id not in assessment_cache:
            assessment_cache[question_data.assessment_id] = (
                await db.execute(
                    select(Assessment)
                    .options(selectinload(Assessment.group).selectinload(Group.curriculum_subject))
                    .where(Assessment.id == question_data.assessment_id)
                )
            ).scalar_one_or_none()
        assessment = assessment_cache[question_data.assessment_id]
        if not assessment:
            errors.append(f"Assessment {question_data.assessment_id} not found.")
        elif teacher.role != "admin" and assessment.teacher_id != teacher.id:
            errors.append("Assessment does not belong to the current teacher.")

    resolved_topic = None
    if not errors and (question_data.topic_id or question_data.topic_tag):
        try:
            resolved_topic = await _resolve_topic(
                db,
                question_data.topic_id,
                question_data.topic_tag,
                assessment,
            )
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
            errors.append(detail.get("message", "Topic validation failed."))

    if question_data.question_type not in {
        "true_false", "yes_no", "mcq_single", "mcq_multi", "image_mcq", "short_answer",
        "essay", "fill_blank", "numeric", "matching", "ordering", "categorization",
        "hotspot", "code", "audio_video", "likert",
    }:
        errors.append("Unsupported question type.")

    if question_data.question_type in {"mcq_single", "mcq_multi", "image_mcq", "true_false", "yes_no"}:
        if len(question_data.options) < 2:
            errors.append("Choice-based questions need at least two options.")
        elif not any(option.is_correct for option in question_data.options):
            errors.append("Choice-based questions require at least one correct option.")

    visible_cases, hidden_cases = _get_code_case_counts(question_data)
    if question_data.question_type == "code":
        if visible_cases + hidden_cases == 0:
            errors.append("Code questions require at least one test case.")
        if hidden_cases == 0:
            warnings.append("No hidden test cases defined.")
        language = (question_data.config or {}).get("language")
        if language and language != "python":
            warnings.append("Non-Python code questions fall back to manual review.")

    if question_data.topic_tag and not resolved_topic:
        warnings.append("Topic tag did not resolve to an existing curriculum topic.")

    return BulkQuestionPreviewItem(
        index=0,
        is_valid=len(errors) == 0,
        question_type=question_data.question_type,
        content_preview=question_data.content[:120],
        assessment_id=question_data.assessment_id,
        assessment_title=assessment.title if assessment else None,
        question_bank_id=question_data.question_bank_id,
        difficulty=question_data.difficulty,
        points=question_data.points,
        topic_tag=question_data.topic_tag,
        resolved_topic_id=resolved_topic.id if resolved_topic else None,
        resolved_topic_name=resolved_topic.name if resolved_topic else None,
        options_count=len(question_data.options),
        visible_test_cases=visible_cases,
        hidden_test_cases=hidden_cases,
        warnings=warnings,
        errors=errors,
    )


@router.post("/assessments/{assessment_id}/questions", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def add_question(
    assessment_id: UUID,
    data: QuestionCreate,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(get_teacher_user),
):
    """Add a question to an assessment."""
    # Verify ownership
    result = await db.execute(
        select(Assessment)
        .options(selectinload(Assessment.group).selectinload(Group.curriculum_subject))
        .where(Assessment.id == assessment_id)
    )
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=404, detail={"code": "ASSESSMENT_NOT_FOUND", "message": "Assessment not found."})
    if teacher.role != "admin" and assessment.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail={"code": "AUTH_INSUFFICIENT_PERMISSIONS", "message": "Not your assessment."})

    topic = await _resolve_topic(db, data.topic_id, data.topic_tag, assessment)

    question = Question(
        assessment_id=assessment_id,
        question_type=data.question_type,
        content=data.content,
        explanation=data.explanation,
        image_url=data.image_url,
        audio_url=data.audio_url,
        video_url=data.video_url,
        points=data.points,
        partial_scoring=data.partial_scoring,
        negative_marking=data.negative_marking,
        order_index=data.order_index,
        topic_tag=topic.name if topic else data.topic_tag,
        topic_id=topic.id if topic else data.topic_id,
        difficulty=data.difficulty,
        blooms_level=data.blooms_level,
        time_suggestion_seconds=data.time_suggestion_seconds,
        config=data.config,
    )
    db.add(question)
    await db.flush()

    # Add options
    for opt_data in data.options:
        option = QuestionOption(
            question_id=question.id,
            content=opt_data.content,
            is_correct=opt_data.is_correct,
            match_key=opt_data.match_key,
            category_key=opt_data.category_key,
            order_position=opt_data.order_position,
            image_url=opt_data.image_url,
        )
        db.add(option)

    await db.flush()
    await db.refresh(question)

    # Reload with options
    result = await db.execute(
        select(Question)
        .options(
            selectinload(Question.options),
            selectinload(Question.topic).selectinload(Topic.module).selectinload(CurriculumModule.subject),
        )
        .where(Question.id == question.id)
    )
    question = result.scalar_one()

    await QuestionRevisionService.create_revision(
        db,
        question.id,
        teacher.id,
        source="manual_create",
        summary="Initial question creation.",
    )

    return SuccessResponse(data=_serialize_question(question))


@router.patch("/questions/{question_id}", response_model=SuccessResponse)
async def update_question(
    question_id: UUID,
    data: QuestionUpdate,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(get_teacher_user),
):
    """Update a question."""
    result = await db.execute(
        select(Question)
        .options(
            selectinload(Question.options),
            selectinload(Question.topic).selectinload(Topic.module).selectinload(CurriculumModule.subject),
            selectinload(Question.assessment).selectinload(Assessment.group).selectinload(Group.curriculum_subject),
        )
        .where(Question.id == question_id)
    )
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail={"code": "QUESTION_NOT_FOUND", "message": "Question not found."})
    if question.assessment and teacher.role != "admin" and question.assessment.teacher_id != teacher.id:
        raise HTTPException(
            status_code=403,
            detail={"code": "AUTH_INSUFFICIENT_PERMISSIONS", "message": "Not your assessment."},
        )

    update_data = data.model_dump(exclude_unset=True)
    if "topic_id" in update_data or "topic_tag" in update_data:
        topic = await _resolve_topic(
            db,
            update_data.get("topic_id"),
            update_data.get("topic_tag"),
            question.assessment,
        )
        update_data["topic_id"] = topic.id if topic else update_data.get("topic_id")
        update_data["topic_tag"] = topic.name if topic else update_data.get("topic_tag")

    for field, value in update_data.items():
        setattr(question, field, value)

    await db.flush()
    question = (
        await db.execute(
            select(Question)
            .options(
                selectinload(Question.options),
                selectinload(Question.topic).selectinload(Topic.module).selectinload(CurriculumModule.subject),
            )
            .where(Question.id == question_id)
        )
    ).scalar_one()
    await QuestionRevisionService.create_revision(
        db,
        question.id,
        teacher.id,
        source="manual_update",
        summary="Question updated from teacher workspace.",
    )
    return SuccessResponse(data=_serialize_question(question))


@router.delete("/questions/{question_id}", response_model=MessageResponse)
async def delete_question(
    question_id: UUID,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(get_teacher_user),
):
    """Delete a question."""
    result = await db.execute(
        select(Question)
        .options(selectinload(Question.assessment))
        .where(Question.id == question_id)
    )
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail={"code": "QUESTION_NOT_FOUND", "message": "Question not found."})
    if question.assessment and teacher.role != "admin" and question.assessment.teacher_id != teacher.id:
        raise HTTPException(
            status_code=403,
            detail={"code": "AUTH_INSUFFICIENT_PERMISSIONS", "message": "Not your assessment."},
        )

    await db.delete(question)
    await db.flush()
    return MessageResponse(message="Question deleted.")


@router.get("/questions/{question_id}/revisions", response_model=SuccessResponse)
async def list_question_revisions(
    question_id: UUID,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(get_teacher_user),
):
    question = (
        await db.execute(
            select(Question)
            .options(selectinload(Question.assessment))
            .where(Question.id == question_id)
        )
    ).scalar_one_or_none()
    if not question:
        raise HTTPException(
            status_code=404,
            detail={"code": "QUESTION_NOT_FOUND", "message": "Question not found."},
        )
    if question.assessment and teacher.role != "admin" and question.assessment.teacher_id != teacher.id:
        raise HTTPException(
            status_code=403,
            detail={"code": "AUTH_INSUFFICIENT_PERMISSIONS", "message": "Not your assessment."},
        )

    revisions = (
        await db.execute(
            select(QuestionRevision)
            .where(QuestionRevision.question_id == question_id)
            .order_by(QuestionRevision.version_number.desc())
        )
    ).scalars().all()

    return SuccessResponse(data=[_serialize_revision(revision) for revision in revisions])


@router.post("/questions/bulk-import/preview", response_model=SuccessResponse)
async def preview_bulk_import_questions(
    payload: Any = Body(...),
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(get_teacher_user),
):
    question_items = _extract_question_items(payload)
    assessment_cache: dict[UUID, Assessment | None] = {}
    preview_items: list[BulkQuestionPreviewItem] = []

    for index, raw_question in enumerate(question_items, start=1):
        preview = await _preview_question_item(db, raw_question, teacher, assessment_cache)
        preview.index = index
        preview_items.append(preview)

    result = BulkQuestionPreviewResponse(
        total_items=len(preview_items),
        valid_items=sum(1 for item in preview_items if item.is_valid),
        invalid_items=sum(1 for item in preview_items if not item.is_valid),
        questions=preview_items,
    )
    return SuccessResponse(data=result)


@router.post("/questions/bulk-import", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def bulk_import_questions(
    data: BulkQuestionImportRequest,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(get_teacher_user),
):
    """Bulk import questions from JSON. Each question can target an assessment or question bank."""
    created = []

    for q_data in data.questions:
        assessment = None
        # Verify assessment ownership if targeting an assessment
        if q_data.assessment_id:
            result = await db.execute(
                select(Assessment)
                .options(selectinload(Assessment.group).selectinload(Group.curriculum_subject))
                .where(Assessment.id == q_data.assessment_id)
            )
            assessment = result.scalar_one_or_none()
            if not assessment:
                raise HTTPException(status_code=404, detail={
                    "code": "ASSESSMENT_NOT_FOUND",
                    "message": f"Assessment {q_data.assessment_id} not found.",
                })
            if teacher.role != "admin" and assessment.teacher_id != teacher.id:
                raise HTTPException(status_code=403, detail={
                    "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                    "message": "Not your assessment.",
                })

        topic = await _resolve_topic(db, q_data.topic_id, q_data.topic_tag, assessment if q_data.assessment_id else None)

        question = Question(
            assessment_id=q_data.assessment_id,
            question_bank_id=q_data.question_bank_id,
            question_type=q_data.question_type,
            content=q_data.content,
            explanation=q_data.explanation,
            image_url=q_data.image_url,
            audio_url=q_data.audio_url,
            video_url=q_data.video_url,
            points=q_data.points,
            partial_scoring=q_data.partial_scoring,
            negative_marking=q_data.negative_marking,
            order_index=q_data.order_index or 0,
            topic_tag=topic.name if topic else q_data.topic_tag,
            topic_id=topic.id if topic else q_data.topic_id,
            difficulty=q_data.difficulty or "medium",
            blooms_level=q_data.blooms_level,
            time_suggestion_seconds=q_data.time_suggestion_seconds,
            config=q_data.config,
        )
        db.add(question)
        await db.flush()

        for opt_data in q_data.options:
            option = QuestionOption(
                question_id=question.id,
                content=opt_data.content,
                is_correct=opt_data.is_correct,
                match_key=opt_data.match_key,
                category_key=opt_data.category_key,
                order_position=opt_data.order_position,
                image_url=opt_data.image_url,
            )
            db.add(option)

        created.append(question)

    await db.flush()

    # Reload with options
    result_questions = []
    for q in created:
        res = await db.execute(
            select(Question)
            .options(
                selectinload(Question.options),
                selectinload(Question.topic).selectinload(Topic.module).selectinload(CurriculumModule.subject),
            )
            .where(Question.id == q.id)
        )
        question = res.scalar_one()
        await QuestionRevisionService.create_revision(
            db,
            question.id,
            teacher.id,
            source="bulk_import",
            summary="Imported through bulk question upload.",
        )
        result_questions.append(question)

    return SuccessResponse(data=[_serialize_question(q) for q in result_questions])
