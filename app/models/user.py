"""
EduTrack — User Model
Roles: admin, teacher, student
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(
        String(20),
        nullable=False,
        index=True,
    )  # admin, teacher, student
    student_id_number = Column(String(50), unique=True, nullable=True)  # for students
    employee_id = Column(String(50), unique=True, nullable=True)  # for teachers
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    extra_time_factor = Column(Float, default=1.0, nullable=False)  # accommodation multiplier
    avatar_url = Column(String(500), nullable=True)
    phone = Column(String(30), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    department = relationship("Department", back_populates="users")
    taught_groups = relationship("Group", back_populates="teacher", foreign_keys="[Group.teacher_id]")
    enrollments = relationship("GroupEnrollment", back_populates="student", foreign_keys="[GroupEnrollment.student_id]")
    assessment_attempts = relationship("AssessmentAttempt", back_populates="student", foreign_keys="[AssessmentAttempt.student_id]")
    created_assessments = relationship("Assessment", back_populates="teacher", foreign_keys="[Assessment.teacher_id]")
    violations = relationship("Violation", back_populates="student", foreign_keys="[Violation.student_id]")
    notifications = relationship("Notification", back_populates="user", foreign_keys="[Notification.user_id]")
    performance_snapshots = relationship("PerformanceSnapshot", back_populates="student", foreign_keys="[PerformanceSnapshot.student_id]")

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"
