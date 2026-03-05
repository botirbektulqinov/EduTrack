"""
EduTrack — Student: Results History API
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
    count: int = (await db.execute(
        select(func.count(AssessmentAttempt.id)).where(
            AssessmentAttempt.student_id == student.id,
            AssessmentAttempt.status.in_(["submitted", "graded", "terminated"]),
        )
    )).scalar() or 0

    query = (
        select(AssessmentAttempt)
        .options(selectinload(AssessmentAttempt.assessment))
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

    items = []
    for a in attempts:
        item = AttemptListResponse.model_validate(a)
        if a.assessment:
            item.assessment_title = a.assessment.title
        items.append(item)

    return SuccessResponse(
        data=items,
        meta=PaginationMeta(page=page, per_page=per_page, total=count, total_pages=(count + per_page - 1) // per_page),
    )


@router.get("/{attempt_id}", response_model=SuccessResponse)
async def result_detail(
    attempt_id: UUID,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(get_student_user),
):
    """Get specific result detail."""
    from app.models.question import Question as QuestionModel
    from app.schemas.question import QuestionResponse

    result = await db.execute(
        select(AssessmentAttempt)
        .options(
            selectinload(AssessmentAttempt.answers),
            selectinload(AssessmentAttempt.assessment)
                .selectinload(Assessment.questions)
                .selectinload(QuestionModel.options),
            selectinload(AssessmentAttempt.violations),
        )
        .where(
            AssessmentAttempt.id == attempt_id,
            AssessmentAttempt.student_id == student.id,
        )
    )
    attempt = result.scalar_one_or_none()
    if not attempt:
        raise HTTPException(status_code=404, detail={"code": "ATTEMPT_NOT_FOUND", "message": "Attempt not found."})

    from app.schemas.attempt import AttemptDetailResponse, StudentAnswerResponse, ViolationResponse
    resp = AttemptDetailResponse.model_validate(attempt)
    resp.answers = [StudentAnswerResponse.model_validate(a) for a in attempt.answers]
    resp.violations = [ViolationResponse.model_validate(v) for v in attempt.violations]
    if attempt.assessment:
        resp.assessment_title = attempt.assessment.title
        resp.questions = [QuestionResponse.model_validate(q) for q in attempt.assessment.questions] if attempt.assessment.questions else []

    return SuccessResponse(data=resp)
