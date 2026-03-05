"""
EduTrack — Violation Schemas
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel


class ViolationCreate(BaseModel):
    violation_type: str
    time_remaining_at_event: Optional[int] = None
    browser_info: Optional[Dict[str, Any]] = None


class ViolationResponse(BaseModel):
    id: UUID
    attempt_id: UUID
    student_id: UUID
    assessment_id: UUID
    violation_type: str
    occurred_at: datetime
    time_remaining_at_event: Optional[int]
    time_deducted_seconds: Optional[int]
    violation_count_after: int
    resolved: bool
    notes: Optional[str]

    model_config = {"from_attributes": True}


class ViolationListResponse(BaseModel):
    id: UUID
    violation_type: str
    occurred_at: datetime
    violation_count_after: int
    resolved: bool

    model_config = {"from_attributes": True}
