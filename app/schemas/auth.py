"""
EduTrack — Auth Schemas
Login, token, password reset.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class UserProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    student_id_number: Optional[str] = None
    employee_id: Optional[str] = None
    department_id: Optional[str] = None
    is_active: bool
    extra_time_factor: float
    avatar_url: Optional[str] = None
    phone: Optional[str] = None

    model_config = {"from_attributes": True}
