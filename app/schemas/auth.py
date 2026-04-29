"""
EduTrack — Auth Schemas
Login, token, password reset.
"""

from uuid import UUID
from typing import Optional
from pydantic import BaseModel, field_validator


def _validate_email_syntax(value: str) -> str:
    normalized = value.strip().lower()
    if (
        not normalized
        or "@" not in normalized
        or normalized.startswith("@")
        or normalized.endswith("@")
        or "." not in normalized.rsplit("@", 1)[1]
        or any(char.isspace() for char in normalized)
    ):
        raise ValueError("Enter a valid email address.")
    return normalized


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _validate_email_syntax(value)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _validate_email_syntax(value)


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class UserProfileResponse(BaseModel):
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

    model_config = {"from_attributes": True}
