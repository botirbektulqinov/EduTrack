"""
EduTrack — Teacher: Analytics API
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_teacher_user
from app.models.user import User
from app.models.assessment import Assessment
from app.schemas.common import SuccessResponse
from app.services.analytics_service import AnalyticsService
from app.services.proctoring_service import ProctoringService

router = APIRouter(tags=["Teacher - Analytics"])


@router.get("/groups/{group_id}/analytics", response_model=SuccessResponse)
async def group_analytics(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(get_teacher_user),
):
    """Get analytics for a teacher's group."""
    data = await AnalyticsService.get_group_analytics(
        db,
        group_id,
        teacher_id=teacher.id if teacher.role != "admin" else None,
    )
    if not data:
        raise HTTPException(status_code=404, detail={"code": "GROUP_NOT_FOUND", "message": "Group not found."})
    return SuccessResponse(data=data)


@router.get("/assessments/{assessment_id}/item-analysis", response_model=SuccessResponse)
async def item_analysis(
    assessment_id: UUID,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(get_teacher_user),
):
    """Get per-question difficulty and discrimination analysis."""
    result = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=404, detail={"code": "ASSESSMENT_NOT_FOUND", "message": "Assessment not found."})
    if teacher.role != "admin" and assessment.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail={"code": "AUTH_INSUFFICIENT_PERMISSIONS", "message": "Not your assessment."})

    analysis = await AnalyticsService.get_item_analysis(db, assessment_id)
    return SuccessResponse(data=analysis)


@router.get("/assessments/{assessment_id}/violations", response_model=SuccessResponse)
async def list_violations(
    assessment_id: UUID,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(get_teacher_user),
):
    """Get all violations for an assessment."""
    result = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=404, detail={"code": "ASSESSMENT_NOT_FOUND", "message": "Assessment not found."})
    if teacher.role != "admin" and assessment.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail={"code": "AUTH_INSUFFICIENT_PERMISSIONS", "message": "Not your assessment."})

    violations = await ProctoringService.get_violations_for_assessment(db, assessment_id)
    from app.schemas.violation import ViolationResponse
    return SuccessResponse(data=[ViolationResponse.model_validate(v) for v in violations])


@router.get("/students/{student_id}/semester-performance", response_model=SuccessResponse)
async def student_semester_performance(
    student_id: UUID,
    semester: str | None = None,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(get_teacher_user),
):
    """Get semester performance dashboard for a student in the teacher's groups."""
    data = await AnalyticsService.get_student_semester_performance(
        db,
        student_id=student_id,
        teacher_id=teacher.id if teacher.role != "admin" else None,
        semester=semester,
    )
    return SuccessResponse(data=data)
