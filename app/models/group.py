"""
EduTrack — Group (Academic Class) Model
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Group(Base):
    __tablename__ = "groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    subject = Column(String(200), nullable=True)
    academic_year = Column(String(20), nullable=True)
    semester = Column(String(20), nullable=True)
    description = Column(Text, nullable=True)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    is_archived = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    teacher = relationship("User", back_populates="taught_groups", foreign_keys=[teacher_id])
    enrollments = relationship("GroupEnrollment", back_populates="group", cascade="all, delete-orphan")
    assessments = relationship("Assessment", back_populates="group", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Group {self.name}>"
