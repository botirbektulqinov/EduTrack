"""
EduTrack — Link Service
Token validation for assessment access links.
"""

from datetime import datetime, timezone
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment
from app.services.assessment_service import AssessmentService


class LinkService:

    @staticmethod
    async def validate_token(
        db: AsyncSession,
        token: UUID,
        student_id: UUID,
    ) -> Tuple[Optional[Assessment], str]:
        """
        Validate an assessment access token.
        Returns (assessment, reason_code).
        """
        assessment = await AssessmentService.get_assessment_by_token(db, token)

        if not assessment:
            return None, "ASSESSMENT_TOKEN_INVALID"

        ok, reason = await AssessmentService.validate_student_access(db, assessment, student_id)
        if not ok:
            return None, reason

        return assessment, "OK"
