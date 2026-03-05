"""
EduTrack — Common Schemas
Shared response wrappers, pagination, etc.
"""

from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class PaginationMeta(BaseModel):
    page: int = 1
    per_page: int = 20
    total: int = 0
    total_pages: int = 0


class SuccessResponse(BaseModel):
    success: bool = True
    data: Any = None
    meta: Optional[PaginationMeta] = None


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


class PaginatedResponse(BaseModel):
    success: bool = True
    data: List[Any] = []
    meta: PaginationMeta


class MessageResponse(BaseModel):
    success: bool = True
    message: str
