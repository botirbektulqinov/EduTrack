"""
EduTrack — Assessment Attempt Model
Tracks each student's session taking an assessment.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship

from app.core.database import Base


ATTEMPT_STATUSES = [
    "not_started",
    "in_progress",
    "submitted",
    "terminated",
    "grading",
    "graded",
]


class AssessmentAttempt(Base):
    __tablename__ = "assessment_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("assessments.id"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    status = Column(
        String(20),
        default="in_progress",
        nullable=False,
    )  # see ATTEMPT_STATUSES

    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    submitted_at = Column(DateTime(timezone=True), nullable=True)

    # Timer
    time_limit_seconds = Column(Integer, nullable=True)  # actual limit incl. accommodations
    time_remaining_seconds = Column(Integer, nullable=True)

    # Scores
    score_raw = Column(Float, nullable=True)
    score_percent = Column(Float, nullable=True)
    grade = Column(String(10), nullable=True)

    # Violations
    violation_count = Column(Integer, default=0, nullable=False)
    termination_reason = Column(String(100), nullable=True)

    # Session security
    server_token = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    assessment = relationship("Assessment", back_populates="attempts")
    student = relationship("User", back_populates="assessment_attempts", foreign_keys=[student_id])
    answers = relationship("StudentAnswer", back_populates="attempt", cascade="all, delete-orphan")
    violations = relationship("Violation", back_populates="attempt", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AssessmentAttempt status={self.status} score={self.score_percent}>"
