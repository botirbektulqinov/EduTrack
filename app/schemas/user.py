"""
EduTrack — User Schemas
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: str  # admin, teacher, student


class UserCreate(UserBase):
    password: str
    student_id_number: Optional[str] = None
    employee_id: Optional[str] = None
    department_id: Optional[UUID] = None
    extra_time_factor: float = 1.0
    phone: Optional[str] = None


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    student_id_number: Optional[str] = None
    employee_id: Optional[str] = None
    department_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    extra_time_factor: Optional[float] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str
    student_id_number: Optional[str] = None
    employee_id: Optional[str] = None
    department_id: Optional[UUID] = None
    is_active: bool
    extra_time_factor: float
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class BulkImportRequest(BaseModel):
    """CSV-style import. Each row: email, full_name, role, password, student_id/employee_id."""
    users: list[UserCreate]
