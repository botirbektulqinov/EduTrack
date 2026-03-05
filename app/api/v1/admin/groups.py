"""
EduTrack — Admin: Group Management API
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_admin_user
from app.models.user import User
from app.models.group import Group
from app.models.group_enrollment import GroupEnrollment
from app.schemas.group import (
    EnrollStudentsRequest,
    GroupCreate,
    GroupDetailResponse,
    GroupListResponse,
    GroupResponse,
    GroupUpdate,
)
from app.schemas.common import MessageResponse, PaginationMeta, SuccessResponse
from app.services.audit_service import AuditService

router = APIRouter(tags=["Admin - Groups"])


@router.get("", response_model=SuccessResponse)
async def list_groups(
    is_archived: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """List all academic groups with teacher name and student count."""
    query = select(Group).options(selectinload(Group.teacher))
    count_query = select(func.count(Group.id))

    if is_archived is not None:
        query = query.where(Group.is_archived == is_archived)
        count_query = count_query.where(Group.is_archived == is_archived)
    if search:
        query = query.where(Group.name.ilike(f"%{search}%"))
        count_query = count_query.where(Group.name.ilike(f"%{search}%"))

    total: int = (await db.execute(count_query)).scalar() or 0
    query = (
        query.order_by(Group.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(query)
    groups = result.scalars().all()

    # Fetch student counts for all groups in one query
    group_ids = [g.id for g in groups]
    if group_ids:
        count_result = await db.execute(
            select(GroupEnrollment.group_id, func.count(GroupEnrollment.id))
            .where(GroupEnrollment.group_id.in_(group_ids))
            .group_by(GroupEnrollment.group_id)
        )
        count_map: dict = {row[0]: row[1] for row in count_result.all()}
    else:
        count_map = {}

    data = []
    for g in groups:
        d = GroupDetailResponse(
            **GroupResponse.model_validate(g).model_dump(),
            teacher_name=g.teacher.full_name if g.teacher else None,
            student_count=count_map.get(g.id, 0),
        )
        data.append(d)

    return SuccessResponse(
        data=[d.model_dump() for d in data],
        meta=PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=(total + per_page - 1) // per_page,
        ),
    )


@router.post("", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    data: GroupCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Create a new academic group."""
    group = Group(
        name=data.name,
        subject=data.subject,
        academic_year=data.academic_year,
        semester=data.semester,
        description=data.description,
        teacher_id=data.teacher_id,
    )
    db.add(group)
    await db.flush()
    await db.refresh(group)

    await AuditService.log(
        db,
        action="GROUP_CREATED",
        actor_id=admin.id,
        actor_role=admin.role,
        target_type="Group",
        target_id=group.id,
    )
    return SuccessResponse(data=GroupResponse.model_validate(group))


@router.get("/{group_id}", response_model=SuccessResponse)
async def get_group(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Get group details."""
    result = await db.execute(
        select(Group).options(selectinload(Group.teacher)).where(Group.id == group_id)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(
            status_code=404,
            detail={"code": "GROUP_NOT_FOUND", "message": "Group not found."},
        )

    # Count students
    student_count = (
        await db.execute(
            select(func.count(GroupEnrollment.id)).where(
                GroupEnrollment.group_id == group_id
            )
        )
    ).scalar() or 0

    data = GroupDetailResponse(
        **GroupResponse.model_validate(group).model_dump(),
        teacher_name=group.teacher.full_name if group.teacher else None,
        student_count=student_count,
    )
    return SuccessResponse(data=data)


@router.patch("/{group_id}", response_model=SuccessResponse)
async def update_group(
    group_id: UUID,
    data: GroupUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Update a group."""
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(
            status_code=404,
            detail={"code": "GROUP_NOT_FOUND", "message": "Group not found."},
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(group, field, value)
    await db.flush()
    await db.refresh(group)

    return SuccessResponse(data=GroupResponse.model_validate(group))


@router.post("/{group_id}/enroll", response_model=MessageResponse)
async def enroll_students(
    group_id: UUID,
    data: EnrollStudentsRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Enroll students into a group by student_id_number."""
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(
            status_code=404,
            detail={"code": "GROUP_NOT_FOUND", "message": "Group not found."},
        )

    # Look up students by student_id_number
    student_result = await db.execute(
        select(User).where(
            User.student_id_number.in_(data.student_ids),
            User.role == "student",
        )
    )
    students = student_result.scalars().all()

    if not students:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "NO_STUDENTS_FOUND",
                "message": "No students found with the given IDs.",
            },
        )

    enrolled = 0
    for student in students:
        existing = await db.execute(
            select(GroupEnrollment).where(
                GroupEnrollment.group_id == group_id,
                GroupEnrollment.student_id == student.id,
            )
        )
        if not existing.scalar_one_or_none():
            enrollment = GroupEnrollment(group_id=group_id, student_id=student.id)
            db.add(enrollment)
            enrolled += 1

    await db.flush()
    await AuditService.log(
        db,
        action="STUDENTS_ENROLLED",
        actor_id=admin.id,
        actor_role=admin.role,
        target_type="Group",
        target_id=group_id,
        metadata={"enrolled_count": enrolled},
    )
    return MessageResponse(message=f"{enrolled} student(s) enrolled successfully.")


@router.get("/{group_id}/students", response_model=SuccessResponse)
async def list_group_students(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """List students enrolled in a group."""
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(
            status_code=404,
            detail={"code": "GROUP_NOT_FOUND", "message": "Group not found."},
        )

    from app.schemas.user import UserListResponse as StudentListResp

    student_result = await db.execute(
        select(User)
        .join(GroupEnrollment, GroupEnrollment.student_id == User.id)
        .where(GroupEnrollment.group_id == group_id)
        .order_by(User.full_name)
    )
    students = student_result.scalars().all()
    return SuccessResponse(data=[StudentListResp.model_validate(s) for s in students])


@router.delete("/{group_id}/students/{student_id}", response_model=MessageResponse)
async def remove_student(
    group_id: UUID,
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Remove a student from a group."""
    result = await db.execute(
        select(GroupEnrollment).where(
            GroupEnrollment.group_id == group_id,
            GroupEnrollment.student_id == student_id,
        )
    )
    enrollment = result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "ENROLLMENT_NOT_FOUND",
                "message": "Student not enrolled in this group.",
            },
        )

    await db.delete(enrollment)
    await db.flush()
    return MessageResponse(message="Student removed from group.")
