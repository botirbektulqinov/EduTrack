"""
EduTrack — Student: Analytics & Dashboard API
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_student_user
from app.models.user import User
from app.models.assessment import Assessment
from app.models.assessment_attempt import AssessmentAttempt
from app.models.group import Group
from app.models.group_enrollment import GroupEnrollment
from app.schemas.common import SuccessResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(tags=["Student - Analytics"])


@router.get("/dashboard", response_model=SuccessResponse)
async def student_dashboard(
    db: AsyncSession = Depends(get_db),
    student: User = Depends(get_student_user),
):
    """Get student's personal performance dashboard data."""
    data = await AnalyticsService.get_student_dashboard(db, student.id)
    return SuccessResponse(data=data)


@router.get("/available-assessments", response_model=SuccessResponse)
async def available_assessments(
    db: AsyncSession = Depends(get_db),
    student: User = Depends(get_student_user),
):
    """Return published, active assessments in groups the student is enrolled in."""
    now = datetime.now(timezone.utc)

    # Get groups the student is enrolled in
    enrolled_group_ids = (await db.execute(
        select(GroupEnrollment.group_id).where(GroupEnrollment.student_id == student.id)
    )).scalars().all()

    if not enrolled_group_ids:
        return SuccessResponse(data=[])

    # Find published + active assessments in those groups within availability window
    query = (
        select(Assessment)
        .options(selectinload(Assessment.group))
        .where(
            Assessment.group_id.in_(enrolled_group_ids),
            Assessment.is_published == True,
            Assessment.is_active == True,
        )
        .order_by(Assessment.available_until.asc().nulls_last(), Assessment.created_at.desc())
    )
    result = await db.execute(query)
    assessments = result.scalars().all()

    # Filter by availability window and max attempts
    items = []
    for a in assessments:
        # Check time window
        if a.available_from and now < a.available_from:
            continue
        if a.available_until and now > a.available_until:
            continue

        # Count student's attempts
        attempt_count = (await db.execute(
            select(func.count(AssessmentAttempt.id)).where(
                AssessmentAttempt.assessment_id == a.id,
                AssessmentAttempt.student_id == student.id,
            )
        )).scalar() or 0

        # Check if any attempt is in progress
        in_progress_result = await db.execute(
            select(AssessmentAttempt).where(
                AssessmentAttempt.assessment_id == a.id,
                AssessmentAttempt.student_id == student.id,
                AssessmentAttempt.status == "in_progress",
            )
        )
        in_progress = in_progress_result.scalar_one_or_none()

        items.append({
            "id": str(a.id),
            "title": a.title,
            "description": a.description,
            "assessment_type": a.assessment_type,
            "group_name": a.group.name if a.group else None,
            "time_limit_minutes": a.time_limit_minutes,
            "available_from": a.available_from.isoformat() if a.available_from else None,
            "available_until": a.available_until.isoformat() if a.available_until else None,
            "max_attempts": a.max_attempts,
            "attempts_used": attempt_count,
            "can_attempt": attempt_count < a.max_attempts,
            "in_progress": in_progress is not None,
            "access_token": str(a.access_token),
        })

    return SuccessResponse(data=items)


@router.get("/subjects", response_model=SuccessResponse)
async def subject_breakdown(
    db: AsyncSession = Depends(get_db),
    student: User = Depends(get_student_user),
):
    """Get per-subject performance breakdown."""
    data = await AnalyticsService.get_subject_breakdown(db, student.id)
    return SuccessResponse(data=data)
