"""
EduTrack — Report Service
Data export for admin reports (CSV, JSON).
"""

import csv
import io
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment
from app.models.assessment_attempt import AssessmentAttempt
from app.models.group import Group
from app.models.user import User
from app.models.violation import Violation


class ReportService:

    @staticmethod
    async def generate_report(
        db: AsyncSession,
        report_type: str,
        period: Optional[str] = None,
    ) -> list[dict]:
        """Generate report data based on type."""
        generators = {
            "users": ReportService._report_users,
            "groups": ReportService._report_groups,
            "assessments": ReportService._report_assessments,
            "results": ReportService._report_results,
            "violations": ReportService._report_violations,
        }
        generator = generators.get(report_type, ReportService._report_users)
        return await generator(db)

    @staticmethod
    async def _report_users(db: AsyncSession) -> list[dict]:
        result = await db.execute(select(User).order_by(User.created_at.desc()))
        users = result.scalars().all()
        return [
            {
                "id": str(u.id),
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "student_id_number": u.student_id_number or "",
                "employee_id": u.employee_id or "",
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else "",
            }
            for u in users
        ]

    @staticmethod
    async def _report_groups(db: AsyncSession) -> list[dict]:
        result = await db.execute(select(Group).order_by(Group.created_at.desc()))
        groups = result.scalars().all()
        return [
            {
                "id": str(g.id),
                "name": g.name,
                "subject": g.subject,
                "academic_year": g.academic_year,
                "semester": g.semester or "",
                "is_archived": g.is_archived,
                "created_at": g.created_at.isoformat() if g.created_at else "",
            }
            for g in groups
        ]

    @staticmethod
    async def _report_assessments(db: AsyncSession) -> list[dict]:
        result = await db.execute(select(Assessment).order_by(Assessment.created_at.desc()))
        assessments = result.scalars().all()
        return [
            {
                "id": str(a.id),
                "title": a.title,
                "assessment_type": a.assessment_type,
                "is_published": a.is_published,
                "is_active": a.is_active,
                "total_points": a.total_points,
                "passing_score": a.passing_score,
                "max_attempts": a.max_attempts,
                "created_at": a.created_at.isoformat() if a.created_at else "",
            }
            for a in assessments
        ]

    @staticmethod
    async def _report_results(db: AsyncSession) -> list[dict]:
        result = await db.execute(
            select(AssessmentAttempt).order_by(AssessmentAttempt.created_at.desc())
        )
        attempts = result.scalars().all()
        return [
            {
                "id": str(a.id),
                "assessment_id": str(a.assessment_id),
                "student_id": str(a.student_id),
                "status": a.status,
                "score_raw": a.score_raw,
                "score_percent": a.score_percent,
                "grade": a.grade or "",
                "violation_count": a.violation_count,
                "started_at": a.started_at.isoformat() if a.started_at else "",
                "submitted_at": a.submitted_at.isoformat() if a.submitted_at else "",
            }
            for a in attempts
        ]

    @staticmethod
    async def _report_violations(db: AsyncSession) -> list[dict]:
        result = await db.execute(
            select(Violation).order_by(Violation.occurred_at.desc())
        )
        violations = result.scalars().all()
        return [
            {
                "id": str(v.id),
                "attempt_id": str(v.attempt_id),
                "student_id": str(v.student_id),
                "assessment_id": str(v.assessment_id),
                "violation_type": v.violation_type,
                "occurred_at": v.occurred_at.isoformat() if v.occurred_at else "",
                "time_deducted_seconds": v.time_deducted_seconds,
                "violation_count_after": v.violation_count_after,
                "resolved": v.resolved,
            }
            for v in violations
        ]

    @staticmethod
    def to_csv(data: list[dict], report_type: str = "report") -> str:
        """Convert list of dicts to CSV string."""
        if not data:
            return ""

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()
