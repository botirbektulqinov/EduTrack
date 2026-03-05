"""
EduTrack — Assessment Model
Types: test, quiz, survey, practice
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    assessment_type = Column(
        String(20),
        nullable=False,
    )  # test, quiz, survey, practice
    format_type = Column(
        String(30),
        default="timed_test",
        nullable=False,
    )  # timed_test, untimed_quiz, adaptive, sectioned, practice, diagnostic, survey
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=True)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Timing
    time_limit_minutes = Column(Integer, nullable=True)
    available_from = Column(DateTime(timezone=True), nullable=True)
    available_until = Column(DateTime(timezone=True), nullable=True)

    # Attempts
    max_attempts = Column(Integer, default=1, nullable=False)
    scoring_policy = Column(
        String(20),
        default="best",
        nullable=False,
    )  # best, last, average

    # Scoring
    passing_score = Column(Float, default=50.0, nullable=False)
    total_points = Column(Float, default=0.0, nullable=False)
    score_release_policy = Column(
        String(30),
        default="immediate",
        nullable=False,
    )  # immediate, after_review, after_window

    # Shuffle / Anti-cheat
    shuffle_questions = Column(Boolean, default=True, nullable=False)
    shuffle_options = Column(Boolean, default=True, nullable=False)

    # Proctoring
    enforce_fullscreen = Column(Boolean, default=True, nullable=False)
    max_violations = Column(Integer, default=3, nullable=False)
    time_penalty_minutes = Column(Integer, default=2, nullable=False)
    block_keyboard_shortcuts = Column(Boolean, default=True, nullable=False)
    tab_switch_detection = Column(Boolean, default=True, nullable=False)
    devtools_detection = Column(Boolean, default=True, nullable=False)
    right_click_block = Column(Boolean, default=True, nullable=False)
    copy_paste_block = Column(Boolean, default=True, nullable=False)
    webcam_proctoring = Column(Boolean, default=False, nullable=False)

    # Access link
    access_token = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)
    password_protected = Column(Boolean, default=False, nullable=False)
    access_password_hash = Column(String(255), nullable=True)

    # Status
    is_published = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    group = relationship("Group", back_populates="assessments")
    teacher = relationship("User", back_populates="created_assessments", foreign_keys=[teacher_id])
    questions = relationship("Question", back_populates="assessment", cascade="all, delete-orphan", order_by="Question.order_index")
    attempts = relationship("AssessmentAttempt", back_populates="assessment", cascade="all, delete-orphan")
    violations = relationship("Violation", back_populates="assessment")

    def __repr__(self):
        return f"<Assessment {self.title} ({self.assessment_type})>"
