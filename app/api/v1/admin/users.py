"""
EduTrack — Admin: User Management API
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_admin_user
from app.models.user import User
from app.schemas.user import (
    BulkImportRequest,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserUpdate,
)
from app.schemas.common import MessageResponse, PaginationMeta, SuccessResponse
from app.services.user_service import UserService
from app.services.audit_service import AuditService

router = APIRouter(tags=["Admin - Users"])


@router.get("", response_model=SuccessResponse)
async def list_users(
    role: Optional[str] = Query(None, description="Filter by role: admin, teacher, student"),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None, description="Search by name or email"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """List all users with optional filters and pagination."""
    users, total = await UserService.list_users(db, role=role, is_active=is_active, search=search, page=page, per_page=per_page)
    return SuccessResponse(
        data=[UserListResponse.model_validate(u) for u in users],
        meta=PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=(total + per_page - 1) // per_page,
        ),
    )


@router.post("", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Create a new user (teacher or student)."""
    existing = await UserService.get_user_by_email(db, data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "USER_EXISTS", "message": "Email already registered."},
        )

    user = await UserService.create_user(db, data)
    await AuditService.log(
        db, action="USER_CREATED", actor_id=admin.id, actor_role=admin.role,
        target_type="User", target_id=user.id,
    )
    return SuccessResponse(data=UserResponse.model_validate(user))


@router.get("/{user_id}", response_model=SuccessResponse)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Get a user by ID."""
    user = await UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail={"code": "USER_NOT_FOUND", "message": "User not found."})
    return SuccessResponse(data=UserResponse.model_validate(user))


@router.patch("/{user_id}", response_model=SuccessResponse)
async def update_user(
    user_id: UUID,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Update a user."""
    user = await UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail={"code": "USER_NOT_FOUND", "message": "User not found."})

    updated = await UserService.update_user(db, user, data)
    await AuditService.log(
        db, action="USER_UPDATED", actor_id=admin.id, actor_role=admin.role,
        target_type="User", target_id=user.id,
    )
    return SuccessResponse(data=UserResponse.model_validate(updated))


@router.delete("/{user_id}", response_model=MessageResponse)
async def deactivate_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Deactivate a user (soft delete)."""
    user = await UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail={"code": "USER_NOT_FOUND", "message": "User not found."})

    await UserService.deactivate_user(db, user)
    await AuditService.log(
        db, action="USER_DEACTIVATED", actor_id=admin.id, actor_role=admin.role,
        target_type="User", target_id=user.id,
    )
    return MessageResponse(message="User deactivated.")


@router.post("/bulk-import", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def bulk_import_users(
    data: BulkImportRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Bulk import users from a list."""
    users = await UserService.bulk_create_users(db, data.users)
    await AuditService.log(
        db, action="USERS_BULK_IMPORTED", actor_id=admin.id, actor_role=admin.role,
        metadata={"count": len(users)},
    )
    return SuccessResponse(data=[UserListResponse.model_validate(u) for u in users])
