"""
EduTrack — Student: Results History API
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_student_user
from app.models.user import User
from app.models.assessment import Assessment
from app.models.assessment_attempt import AssessmentAttempt
from app.schemas.attempt import AttemptListResponse
from app.schemas.common import PaginationMeta, SuccessResponse

router = APIRouter(tags=["Student - Results"])


@router.get("", response_model=SuccessResponse)
async def my_results(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    student: User = Depends(get_student_user),
):
    """Get all my assessment results."""
    count = (await db.execute(
        select(func.count(AssessmentAttempt.id)).where(
            AssessmentAttempt.student_id == student.id,
            AssessmentAttempt.status.in_(["submitted", "graded", "terminated"]),
        )
    )).scalar()

    query = (
        select(AssessmentAttempt)
        .where(
            AssessmentAttempt.student_id == student.id,
            AssessmentAttempt.status.in_(["submitted", "graded", "terminated"]),
        )
        .order_by(AssessmentAttempt.submitted_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(query)
    attempts = result.scalars().all()

    return SuccessResponse(
        data=[AttemptListResponse.model_validate(a) for a in attempts],
        meta=PaginationMeta(page=page, per_page=per_page, total=count, total_pages=(count + per_page - 1) // per_page),
    )


@router.get("/{attempt_id}", response_model=SuccessResponse)
async def result_detail(
    attempt_id: UUID,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(get_student_user),
):
    """Get specific result detail."""
    result = await db.execute(
        select(AssessmentAttempt).where(
            AssessmentAttempt.id == attempt_id,
            AssessmentAttempt.student_id == student.id,
        )
    )
    attempt = result.scalar_one_or_none()
    if not attempt:
        raise HTTPException(status_code=404, detail={"code": "ATTEMPT_NOT_FOUND", "message": "Attempt not found."})

    return SuccessResponse(data=AttemptListResponse.model_validate(attempt))
