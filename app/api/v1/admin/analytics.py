"""
EduTrack — Admin: Analytics & Reports API
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_admin_user
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.services.analytics_service import AnalyticsService
from app.services.report_service import ReportService

router = APIRouter(tags=["Admin - Analytics"])


@router.get("/analytics/overview", response_model=SuccessResponse)
async def admin_overview(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Get university-wide dashboard data."""
    data = await AnalyticsService.get_admin_overview(db)
    return SuccessResponse(data=data)


@router.get("/analytics/violations", response_model=SuccessResponse)
async def violation_summary(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Get violation summary across all assessments."""
    overview = await AnalyticsService.get_admin_overview(db)
    return SuccessResponse(data=overview.get("violation_summary", {}))


@router.get("/reports/export")
async def export_report(
    format: str = Query("csv", description="Export format: csv, json"),
    report_type: str = Query("users", description="Report type: users, groups, assessments, results, violations"),
    period: Optional[str] = Query(None, description="Period filter: current_semester, academic_year, or YYYY-MM-DD:YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Export a report as CSV or JSON."""
    data = await ReportService.generate_report(db, report_type=report_type, period=period)

    if format == "json":
        return SuccessResponse(data=data)

    # CSV export
    csv_content = ReportService.to_csv(data, report_type=report_type)
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=edutrack_{report_type}_report.csv"},
    )
