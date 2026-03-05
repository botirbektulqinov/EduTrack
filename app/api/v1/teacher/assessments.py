"""
EduTrack — Teacher: Assessment Management API
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_teacher_user
from app.models.user import User
from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentListResponse,
    AssessmentResponse,
    AssessmentUpdate,
)
from app.schemas.common import MessageResponse, PaginationMeta, SuccessResponse
from app.services.assessment_service import AssessmentService
from app.services.audit_service import AuditService

router = APIRouter(tags=["Teacher - Assessments"])


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
    return SuccessResponse(
        data=[AssessmentListResponse.model_validate(a) for a in assessments],
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
    return SuccessResponse(data=AssessmentResponse.model_validate(assessment))


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

    return SuccessResponse(data=AssessmentResponse.model_validate(assessment))


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
    return SuccessResponse(data=AssessmentResponse.model_validate(updated))


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
    return SuccessResponse(data=AssessmentResponse.model_validate(published))


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
    return SuccessResponse(data=AssessmentResponse.model_validate(assessment))


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
