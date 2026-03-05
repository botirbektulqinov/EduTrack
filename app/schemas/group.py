"""
EduTrack — Group Schemas
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class GroupBase(BaseModel):
    name: str
    subject: Optional[str] = None
    academic_year: Optional[str] = None
    semester: Optional[str] = None
    description: Optional[str] = None


class GroupCreate(GroupBase):
    teacher_id: Optional[UUID] = None


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    academic_year: Optional[str] = None
    semester: Optional[str] = None
    description: Optional[str] = None
    teacher_id: Optional[UUID] = None
    is_archived: Optional[bool] = None


class GroupResponse(GroupBase):
    id: UUID
    teacher_id: Optional[UUID] = None
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GroupDetailResponse(GroupResponse):
    teacher_name: Optional[str] = None
    student_count: int = 0


class EnrollStudentsRequest(BaseModel):
    student_ids: List[UUID]


class GroupListResponse(BaseModel):
    id: UUID
    name: str
    subject: Optional[str] = None
    academic_year: Optional[str] = None
    semester: Optional[str] = None
    is_archived: bool
    student_count: int = 0

    model_config = {"from_attributes": True}
