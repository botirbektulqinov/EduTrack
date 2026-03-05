"""
EduTrack — User Service
CRUD operations and business logic for user management.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserService:

    @staticmethod
    async def create_user(db: AsyncSession, data: UserCreate) -> User:
        """Create a new user with hashed password."""
        user = User(
            email=data.email,
            full_name=data.full_name,
            role=data.role,
            password_hash=hash_password(data.password),
            student_id_number=data.student_id_number,
            employee_id=data.employee_id,
            department_id=data.department_id,
            extra_time_factor=data.extra_time_factor,
            phone=data.phone,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def authenticate(db: AsyncSession, email: str, password: str) -> Optional[User]:
        """Verify email + password. Returns user if valid, else None."""
        user = await UserService.get_user_by_email(db, email)
        if not user or not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    @staticmethod
    async def list_users(
        db: AsyncSession,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[List[User], int]:
        """List users with optional filters, pagination."""
        query = select(User)
        count_query = select(func.count(User.id))

        if role:
            query = query.where(User.role == role)
            count_query = count_query.where(User.role == role)
        if is_active is not None:
            query = query.where(User.is_active == is_active)
            count_query = count_query.where(User.is_active == is_active)
        if search:
            search_filter = User.full_name.ilike(f"%{search}%") | User.email.ilike(f"%{search}%")
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        total: int = (await db.execute(count_query)).scalar() or 0
        query = query.order_by(User.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await db.execute(query)
        return list(result.scalars().all()), total

    @staticmethod
    async def update_user(db: AsyncSession, user: User, data: UserUpdate) -> User:
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        await db.flush()
        await db.refresh(user)
        return user

    @staticmethod
    async def deactivate_user(db: AsyncSession, user: User) -> User:
        user.is_active = False
        await db.flush()
        await db.refresh(user)
        return user

    @staticmethod
    async def reset_password(db: AsyncSession, user: User, new_password: str) -> User:
        user.password_hash = hash_password(new_password)
        await db.flush()
        return user

    @staticmethod
    async def bulk_create_users(db: AsyncSession, users_data: List[UserCreate]) -> List[User]:
        """Bulk import users."""
        users = []
        for data in users_data:
            user = User(
                email=data.email,
                full_name=data.full_name,
                role=data.role,
                password_hash=hash_password(data.password),
                student_id_number=data.student_id_number,
                employee_id=data.employee_id,
                department_id=data.department_id,
                extra_time_factor=data.extra_time_factor,
                phone=data.phone,
            )
            db.add(user)
            users.append(user)
        await db.flush()
        for u in users:
            await db.refresh(u)
        return users
