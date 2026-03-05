"""
EduTrack — Group Enrollment (many-to-many: Group <-> Student)
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class GroupEnrollment(Base):
    __tablename__ = "group_enrollments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    enrolled_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("group_id", "student_id", name="uq_group_enrollments_group_student"),
    )

    # Relationships
    group = relationship("Group", back_populates="enrollments")
    student = relationship("User", back_populates="enrollments", foreign_keys=[student_id])

    def __repr__(self):
        return f"<GroupEnrollment group={self.group_id} student={self.student_id}>"
