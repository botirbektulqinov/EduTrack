"""
EduTrack — Teacher: Assessment Management API
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_teacher_user
from app.models.user import User
from app.models.group import Group
from app.models.subject import Subject
from app.schemas.question import QuestionResponse
from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentListResponse,
    AssessmentResponse,
    AssessmentUpdate,
)
from app.schemas.common import MessageResponse, PaginationMeta, SuccessResponse
from app.services.assessment_service import AssessmentService
from app.services.audit_service import AuditService
from app.services.curriculum_service import CurriculumService

router = APIRouter(tags=["Teacher - Assessments"])


def _enrich_response(assessment) -> AssessmentResponse:
    """Convert ORM assessment to AssessmentResponse with group_name and question_count."""
    resp = AssessmentResponse.model_validate(assessment)
    resp.group_name = assessment.group.name if assessment.group else None
    resp.subject_id = CurriculumService.assessment_subject_id(assessment)
    resp.subject_name = CurriculumService.assessment_subject_name(assessment)
    resp.group_subject_id = assessment.group.subject_id if assessment.group else None
    resp.group_subject_name = CurriculumService.group_subject_name(assessment.group)
    resp.question_count = len(assessment.questions) if assessment.questions else 0
    resp.questions = [_serialize_question(question) for question in assessment.questions]
    return resp


def _serialize_question(question) -> QuestionResponse:
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


@router.get("/groups", response_model=SuccessResponse)
async def list_teacher_groups(
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(get_teacher_user),
):
    """List groups owned by this teacher (for assessment creation)."""
    result = await db.execute(
        select(Group)
        .options(selectinload(Group.curriculum_subject))
        .where(Group.teacher_id == teacher.id, Group.is_archived == False)
    )
    groups = result.scalars().all()
    return SuccessResponse(
        data=[
            {
                "id": str(g.id),
                "name": g.name,
                "subject": g.subject,
                "subject_id": str(g.subject_id) if g.subject_id else None,
                "subject_name": CurriculumService.group_subject_name(g),
            }
            for g in groups
        ],
    )


@router.get("/subjects", response_model=SuccessResponse)
async def list_curriculum_subjects(
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(get_teacher_user),
):
    subjects = (
        await db.execute(select(Subject).order_by(Subject.name))
    ).scalars().all()
    return SuccessResponse(
        data=[
            {
                "id": str(subject.id),
                "name": subject.name,
                "code": subject.code,
            }
            for subject in subjects
        ],
    )


@router.get("", response_model=SuccessResponse)
async def list_assessments(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(get_teacher_user),
):
    """List all assessments created by this teacher."""
    assessments, total = await AssessmentService.list_teacher_assessments(
        db, teacher.id, page=page, per_page=per_page,
    )
    items = []
    for a in assessments:
        item = AssessmentListResponse.model_validate(a)
        item.group_name = a.group.name if a.group else None
        item.subject_id = CurriculumService.assessment_subject_id(a)
        item.subject_name = CurriculumService.assessment_subject_name(a)
        item.group_subject_id = a.group.subject_id if a.group else None
        item.group_subject_name = CurriculumService.group_subject_name(a.group)
        item.question_count = len(a.questions) if a.questions else 0
        items.append(item)
    return SuccessResponse(
        data=items,
        meta=PaginationMeta(page=page, per_page=per_page, total=total, total_pages=(total + per_page - 1) // per_page),
    )


@router.post("", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_assessment(
    data: AssessmentCreate,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(get_teacher_user),
):
    """Create a new assessment."""
    assessment = await AssessmentService.create_assessment(db, teacher.id, data)
    await AuditService.log(
        db, action="ASSESSMENT_CREATED", actor_id=teacher.id, actor_role=teacher.role,
        target_type="Assessment", target_id=assessment.id,
    )
    # Re-fetch to eagerly load relationships
    assessment = await AssessmentService.get_assessment(db, assessment.id)
    return SuccessResponse(data=_enrich_response(assessment))


@router.get("/{assessment_id}", response_model=SuccessResponse)
async def get_assessment(
    assessment_id: UUID,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(get_teacher_user),
):
    """Get assessment details with questions."""
    assessment = await AssessmentService.get_assessment(db, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail={"code": "ASSESSMENT_NOT_FOUND", "message": "Assessment not found."})

    # Teachers can only view their own (unless admin)
    if teacher.role != "admin" and assessment.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail={"code": "AUTH_INSUFFICIENT_PERMISSIONS", "message": "Not your assessment."})

    return SuccessResponse(data=_enrich_response(assessment))


@router.patch("/{assessment_id}", response_model=SuccessResponse)
async def update_assessment(
    assessment_id: UUID,
    data: AssessmentUpdate,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(get_teacher_user),
):
    """Update an assessment (only draft/unpublished)."""
    assessment = await AssessmentService.get_assessment(db, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail={"code": "ASSESSMENT_NOT_FOUND", "message": "Assessment not found."})
    if teacher.role != "admin" and assessment.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail={"code": "AUTH_INSUFFICIENT_PERMISSIONS", "message": "Not your assessment."})

    updated = await AssessmentService.update_assessment(db, assessment, data)
    # Re-fetch to eagerly load relationships
    updated = await AssessmentService.get_assessment(db, updated.id)
    return SuccessResponse(data=_enrich_response(updated))


@router.delete("/{assessment_id}", response_model=MessageResponse)
async def delete_assessment(
    assessment_id: UUID,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(get_teacher_user),
):
    """Delete a draft assessment."""
    assessment = await AssessmentService.get_assessment(db, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail={"code": "ASSESSMENT_NOT_FOUND", "message": "Assessment not found."})
    if teacher.role != "admin" and assessment.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail={"code": "AUTH_INSUFFICIENT_PERMISSIONS", "message": "Not your assessment."})
    if assessment.is_published:
        raise HTTPException(status_code=400, detail={"code": "CANNOT_DELETE_PUBLISHED", "message": "Cannot delete a published assessment. Unpublish first."})

    await AssessmentService.delete_assessment(db, assessment)
    await AuditService.log(
        db, action="ASSESSMENT_DELETED", actor_id=teacher.id, actor_role=teacher.role,
        target_type="Assessment", target_id=assessment_id,
    )
    return MessageResponse(message="Assessment deleted.")


@router.post("/{assessment_id}/publish", response_model=SuccessResponse)
async def publish_assessment(
    assessment_id: UUID,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(get_teacher_user),
):
    """Publish an assessment — generates access link."""
    assessment = await AssessmentService.get_assessment(db, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail={"code": "ASSESSMENT_NOT_FOUND", "message": "Assessment not found."})
    if teacher.role != "admin" and assessment.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail={"code": "AUTH_INSUFFICIENT_PERMISSIONS", "message": "Not your assessment."})

    published = await AssessmentService.publish_assessment(db, assessment)
    await AuditService.log(
        db, action="ASSESSMENT_PUBLISHED", actor_id=teacher.id, actor_role=teacher.role,
        target_type="Assessment", target_id=assessment.id,
    )
    # Re-fetch to eagerly load relationships
    published = await AssessmentService.get_assessment(db, published.id)
    return SuccessResponse(data=_enrich_response(published))


@router.post("/{assessment_id}/unpublish", response_model=SuccessResponse)
async def unpublish_assessment(
    assessment_id: UUID,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(get_teacher_user),
):
    """Unpublish an assessment."""
    assessment = await AssessmentService.get_assessment(db, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail={"code": "ASSESSMENT_NOT_FOUND", "message": "Assessment not found."})
    if teacher.role != "admin" and assessment.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail={"code": "AUTH_INSUFFICIENT_PERMISSIONS", "message": "Not your assessment."})

    await AssessmentService.unpublish_assessment(db, assessment)
    # Re-fetch to eagerly load relationships
    assessment = await AssessmentService.get_assessment(db, assessment.id)
    return SuccessResponse(data=_enrich_response(assessment))


@router.post("/{assessment_id}/deactivate", response_model=MessageResponse)
async def deactivate_assessment(
    assessment_id: UUID,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(get_teacher_user),
):
    """Deactivate the assessment link immediately."""
    assessment = await AssessmentService.get_assessment(db, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail={"code": "ASSESSMENT_NOT_FOUND", "message": "Assessment not found."})
    if teacher.role != "admin" and assessment.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail={"code": "AUTH_INSUFFICIENT_PERMISSIONS", "message": "Not your assessment."})

    await AssessmentService.deactivate_assessment(db, assessment)
    await AuditService.log(
        db, action="ASSESSMENT_DEACTIVATED", actor_id=teacher.id, actor_role=teacher.role,
        target_type="Assessment", target_id=assessment.id,
    )
    return MessageResponse(message="Assessment link deactivated.")
