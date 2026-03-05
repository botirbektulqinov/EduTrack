"""
EduTrack — Admin: Analytics & Reports API
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_admin_user
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(tags=["Admin - Analytics"])


@router.get("/overview", response_model=SuccessResponse)
async def admin_overview(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Get university-wide dashboard data."""
    data = await AnalyticsService.get_admin_overview(db)
    return SuccessResponse(data=data)


@router.get("/violations", response_model=SuccessResponse)
async def violation_summary(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Get violation summary across all assessments."""
    # Reuse admin overview for now; in production, this would be separate
    overview = await AnalyticsService.get_admin_overview(db)
    return SuccessResponse(data=overview.get("violation_summary", {}))
