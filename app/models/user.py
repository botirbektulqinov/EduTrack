"""
EduTrack — User Model
Roles: admin, teacher, student
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.assessment import Assessment
    from app.models.assessment_attempt import AssessmentAttempt
    from app.models.department import Department
    from app.models.group import Group
    from app.models.group_enrollment import GroupEnrollment
    from app.models.notification import Notification
    from app.models.performance_snapshot import PerformanceSnapshot
    from app.models.violation import Violation


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), index=True)  # admin | teacher | student
    student_id_number: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True)
    employee_id: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True)
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    extra_time_factor: Mapped[float] = mapped_column(Float, default=1.0)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ──
    department: Mapped[Optional["Department"]] = relationship(back_populates="users")
    taught_groups: Mapped[list["Group"]] = relationship(
        back_populates="teacher", foreign_keys="[Group.teacher_id]",
    )
    enrollments: Mapped[list["GroupEnrollment"]] = relationship(
        back_populates="student", foreign_keys="[GroupEnrollment.student_id]",
    )
    assessment_attempts: Mapped[list["AssessmentAttempt"]] = relationship(
        back_populates="student", foreign_keys="[AssessmentAttempt.student_id]",
    )
    created_assessments: Mapped[list["Assessment"]] = relationship(
        back_populates="teacher", foreign_keys="[Assessment.teacher_id]",
    )
    violations: Mapped[list["Violation"]] = relationship(
        back_populates="student", foreign_keys="[Violation.student_id]",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="user", foreign_keys="[Notification.user_id]",
    )
    performance_snapshots: Mapped[list["PerformanceSnapshot"]] = relationship(
        back_populates="student", foreign_keys="[PerformanceSnapshot.student_id]",
    )

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"
