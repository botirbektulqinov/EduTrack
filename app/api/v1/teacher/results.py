"""
EduTrack — Teacher: Results & Grading API
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_teacher_user
from app.models.user import User
from app.models.assessment import Assessment
from app.models.assessment_attempt import AssessmentAttempt
from app.models.student_answer import StudentAnswer
from app.schemas.attempt import (
    AttemptDetailResponse,
    AttemptListResponse,
    BulkManualGradeRequest,
)
from app.schemas.common import MessageResponse, PaginationMeta, SuccessResponse
from app.services.grading_service import GradingService

router = APIRouter(tags=["Teacher - Results & Grading"])


@router.get("/assessments/{assessment_id}/attempts", response_model=SuccessResponse)
async def list_attempts(
    assessment_id: UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(get_teacher_user),
):
    """List all attempts for an assessment."""
    # Verify ownership
    result = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=404, detail={"code": "ASSESSMENT_NOT_FOUND", "message": "Assessment not found."})
    if teacher.role != "admin" and assessment.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail={"code": "AUTH_INSUFFICIENT_PERMISSIONS", "message": "Not your assessment."})

    from sqlalchemy import func
    count = (await db.execute(
        select(func.count(AssessmentAttempt.id)).where(AssessmentAttempt.assessment_id == assessment_id)
    )).scalar() or 0

    query = (
        select(AssessmentAttempt)
        .where(AssessmentAttempt.assessment_id == assessment_id)
        .order_by(AssessmentAttempt.started_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(query)
    attempts = result.scalars().all()

    return SuccessResponse(
        data=[AttemptListResponse.model_validate(a) for a in attempts],
        meta=PaginationMeta(page=page, per_page=per_page, total=count, total_pages=(count + per_page - 1) // per_page),
    )


@router.get("/attempts/{attempt_id}", response_model=SuccessResponse)
async def get_attempt_detail(
    attempt_id: UUID,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(get_teacher_user),
):
    """Get detailed attempt with answers and violations."""
    result = await db.execute(
        select(AssessmentAttempt)
        .options(
            selectinload(AssessmentAttempt.answers),
            selectinload(AssessmentAttempt.violations),
        )
        .where(AssessmentAttempt.id == attempt_id)
    )
    attempt = result.scalar_one_or_none()
    if not attempt:
        raise HTTPException(status_code=404, detail={"code": "ATTEMPT_NOT_FOUND", "message": "Attempt not found."})

    return SuccessResponse(data=AttemptDetailResponse.model_validate(attempt))


@router.patch("/attempts/{attempt_id}/grade", response_model=SuccessResponse)
async def manual_grade(
    attempt_id: UUID,
    data: BulkManualGradeRequest,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(get_teacher_user),
):
    """Manually grade answers in an attempt (essay, code, etc.)."""
    result = await db.execute(
        select(AssessmentAttempt)
        .options(selectinload(AssessmentAttempt.answers))
        .where(AssessmentAttempt.id == attempt_id)
    )
    attempt = result.scalar_one_or_none()
    if not attempt:
        raise HTTPException(status_code=404, detail={"code": "ATTEMPT_NOT_FOUND", "message": "Attempt not found."})

    answers_map = {str(a.question_id): a for a in attempt.answers}

    for grade in data.grades:
        answer = answers_map.get(str(grade.question_id))
        if answer:
            answer.score_awarded = grade.score_awarded
            answer.teacher_feedback = grade.teacher_feedback
            answer.auto_graded = False

    # Recalculate total score
    total_earned = sum(a.score_awarded or 0 for a in attempt.answers)
    # Get total points from assessment
    assessment = await db.execute(select(Assessment).where(Assessment.id == attempt.assessment_id))
    assessment = assessment.scalar_one()

    attempt.score_raw = total_earned
    attempt.score_percent = (total_earned / assessment.total_points * 100) if assessment.total_points > 0 else 0
    attempt.grade = GradingService._compute_grade(attempt.score_percent or 0)
    attempt.status = "graded"

    await db.flush()
    return SuccessResponse(data=AttemptListResponse.model_validate(attempt))
