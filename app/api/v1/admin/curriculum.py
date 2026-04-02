"""
EduTrack - Admin: Curriculum Management API
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_admin_user
from app.core.database import get_db
from app.models.assessment import Assessment
from app.models.curriculum_module import CurriculumModule
from app.models.group import Group
from app.models.question import Question
from app.models.subject import Subject
from app.models.topic import Topic
from app.models.user import User
from app.schemas.common import MessageResponse, SuccessResponse
from app.schemas.curriculum import (
    CurriculumModuleCreate,
    CurriculumModuleResponse,
    CurriculumModuleUpdate,
    GroupSubjectAssignmentRequest,
    QuestionTopicAssignmentRequest,
    SubjectCreate,
    SubjectResponse,
    SubjectTreeResponse,
    SubjectUpdate,
    TopicCreate,
    TopicResponse,
    TopicUpdate,
)
from app.services.curriculum_service import CurriculumService

router = APIRouter(tags=["Admin - Curriculum"])


def _serialize_topic(topic: Topic) -> TopicResponse:
    payload = TopicResponse.model_validate(topic)
    payload.module_name = topic.module.name if topic.module else None
    payload.subject_id = topic.module.subject_id if topic.module else None
    payload.subject_name = topic.module.subject.name if topic.module and topic.module.subject else None
    return payload


def _serialize_tree(subject: Subject) -> SubjectTreeResponse:
    return SubjectTreeResponse.model_validate({
        **SubjectResponse.model_validate(subject).model_dump(),
        "modules": [
            {
                **CurriculumModuleResponse.model_validate(module).model_dump(),
                "topics": [
                    _serialize_topic(topic).model_dump() for topic in module.topics
                ],
            }
            for module in subject.modules
        ],
    })


@router.get("/tree", response_model=SuccessResponse)
async def get_curriculum_tree(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    subjects = await CurriculumService.list_tree(db)
    return SuccessResponse(data={"subjects": [_serialize_tree(subject).model_dump() for subject in subjects]})


@router.get("/review-queue", response_model=SuccessResponse)
async def get_review_queue(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    queue = await CurriculumService.get_review_queue(db)
    return SuccessResponse(data=queue)


@router.post("/sync-legacy", response_model=SuccessResponse)
async def sync_legacy_curriculum(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    result = await CurriculumService.sync_legacy_data(db)
    return SuccessResponse(data=result)


@router.post("/subjects", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_subject(
    data: SubjectCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    existing = await CurriculumService.find_subject_by_name(db, data.name)
    if existing:
        raise HTTPException(
            status_code=400,
            detail={"code": "SUBJECT_EXISTS", "message": "A subject with this name already exists."},
        )

    subject = Subject(name=data.name.strip(), code=data.code, description=data.description)
    db.add(subject)
    await db.flush()
    await db.refresh(subject)
    return SuccessResponse(data=SubjectResponse.model_validate(subject))


@router.patch("/subjects/{subject_id}", response_model=SuccessResponse)
async def update_subject(
    subject_id: UUID,
    data: SubjectUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    subject = await db.get(Subject, subject_id)
    if not subject:
        raise HTTPException(
            status_code=404,
            detail={"code": "SUBJECT_NOT_FOUND", "message": "Subject not found."},
        )

    update_data = data.model_dump(exclude_unset=True)
    if "name" in update_data and update_data["name"]:
        existing = await CurriculumService.find_subject_by_name(db, update_data["name"])
        if existing and existing.id != subject.id:
            raise HTTPException(
                status_code=400,
                detail={"code": "SUBJECT_EXISTS", "message": "A subject with this name already exists."},
            )

    for field, value in update_data.items():
        setattr(subject, field, value.strip() if isinstance(value, str) else value)

    await db.flush()
    await db.refresh(subject)
    return SuccessResponse(data=SubjectResponse.model_validate(subject))


@router.post("/modules", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_module(
    data: CurriculumModuleCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    subject = await db.get(Subject, data.subject_id)
    if not subject:
        raise HTTPException(
            status_code=404,
            detail={"code": "SUBJECT_NOT_FOUND", "message": "Subject not found."},
        )

    module = CurriculumModule(
        subject_id=data.subject_id,
        name=data.name.strip(),
        description=data.description,
        order_index=data.order_index,
    )
    db.add(module)
    await db.flush()
    await db.refresh(module)
    return SuccessResponse(data=CurriculumModuleResponse.model_validate(module))


@router.patch("/modules/{module_id}", response_model=SuccessResponse)
async def update_module(
    module_id: UUID,
    data: CurriculumModuleUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    module = await db.get(CurriculumModule, module_id)
    if not module:
        raise HTTPException(
            status_code=404,
            detail={"code": "MODULE_NOT_FOUND", "message": "Module not found."},
        )

    if data.subject_id:
        subject = await db.get(Subject, data.subject_id)
        if not subject:
            raise HTTPException(
                status_code=404,
                detail={"code": "SUBJECT_NOT_FOUND", "message": "Subject not found."},
            )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(module, field, value.strip() if isinstance(value, str) else value)

    await db.flush()
    await db.refresh(module)
    return SuccessResponse(data=CurriculumModuleResponse.model_validate(module))


@router.post("/topics", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_topic(
    data: TopicCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    module = (
        await db.execute(
            select(CurriculumModule)
            .options(selectinload(CurriculumModule.subject))
            .where(CurriculumModule.id == data.module_id)
        )
    ).scalar_one_or_none()
    if not module:
        raise HTTPException(
            status_code=404,
            detail={"code": "MODULE_NOT_FOUND", "message": "Module not found."},
        )

    topic = Topic(
        module_id=data.module_id,
        name=data.name.strip(),
        description=data.description,
        order_index=data.order_index,
    )
    db.add(topic)
    await db.flush()

    topic = (
        await db.execute(
            select(Topic)
            .options(selectinload(Topic.module).selectinload(CurriculumModule.subject))
            .where(Topic.id == topic.id)
        )
    ).scalar_one()
    return SuccessResponse(data=_serialize_topic(topic))


@router.patch("/topics/{topic_id}", response_model=SuccessResponse)
async def update_topic(
    topic_id: UUID,
    data: TopicUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
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

    if data.module_id:
        module = await db.get(CurriculumModule, data.module_id)
        if not module:
            raise HTTPException(
                status_code=404,
                detail={"code": "MODULE_NOT_FOUND", "message": "Module not found."},
            )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(topic, field, value.strip() if isinstance(value, str) else value)

    await db.flush()

    topic = (
        await db.execute(
            select(Topic)
            .options(selectinload(Topic.module).selectinload(CurriculumModule.subject))
            .where(Topic.id == topic_id)
        )
    ).scalar_one()
    return SuccessResponse(data=_serialize_topic(topic))


@router.patch("/groups/{group_id}/subject", response_model=MessageResponse)
async def assign_group_subject(
    group_id: UUID,
    data: GroupSubjectAssignmentRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    group = await db.get(Group, group_id)
    if not group:
        raise HTTPException(
            status_code=404,
            detail={"code": "GROUP_NOT_FOUND", "message": "Group not found."},
        )

    subject = await db.get(Subject, data.subject_id)
    if not subject:
        raise HTTPException(
            status_code=404,
            detail={"code": "SUBJECT_NOT_FOUND", "message": "Subject not found."},
        )

    await CurriculumService.assign_group_subject(db, group, subject)
    return MessageResponse(message="Group mapped to curriculum subject.")


@router.patch("/questions/{question_id}/topic", response_model=MessageResponse)
async def assign_question_topic(
    question_id: UUID,
    data: QuestionTopicAssignmentRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    question = (
        await db.execute(
            select(Question)
            .options(selectinload(Question.assessment).selectinload(Assessment.group).selectinload(Group.curriculum_subject))
            .where(Question.id == question_id)
        )
    ).scalar_one_or_none()
    if not question:
        raise HTTPException(
            status_code=404,
            detail={"code": "QUESTION_NOT_FOUND", "message": "Question not found."},
        )

    topic = (
        await db.execute(
            select(Topic)
            .options(selectinload(Topic.module).selectinload(CurriculumModule.subject))
            .where(Topic.id == data.topic_id)
        )
    ).scalar_one_or_none()
    if not topic:
        raise HTTPException(
            status_code=404,
            detail={"code": "TOPIC_NOT_FOUND", "message": "Topic not found."},
        )

    assessment_subject_id = CurriculumService.assessment_subject_id(question.assessment)
    if assessment_subject_id:
        if topic.module.subject_id != assessment_subject_id:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "TOPIC_SUBJECT_MISMATCH",
                    "message": "Selected topic does not belong to the question's assessment subject.",
                },
            )

    await CurriculumService.assign_question_topic(db, question, topic)
    return MessageResponse(message="Question mapped to curriculum topic.")
