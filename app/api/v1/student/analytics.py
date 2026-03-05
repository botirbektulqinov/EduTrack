"""
EduTrack — Student: Analytics & Dashboard API
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_student_user
from app.models.user import User
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


@router.get("/subjects", response_model=SuccessResponse)
async def subject_breakdown(
    db: AsyncSession = Depends(get_db),
    student: User = Depends(get_student_user),
):
    """Get per-subject performance breakdown."""
    # Placeholder — requires joining attempts with assessments and groups
    return SuccessResponse(data=[])
