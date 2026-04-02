"""
EduTrack — Assessment Model
Quiz / Exam configuration with full proctoring controls.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.assessment_attempt import AssessmentAttempt
    from app.models.group import Group
    from app.models.question import Question
    from app.models.subject import Subject
    from app.models.user import User
    from app.models.violation import Violation


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Type & format
    assessment_type: Mapped[str] = mapped_column(String(30), default="quiz")
    format_type: Mapped[str] = mapped_column(String(30), default="standard")

    # Ownership
    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=True,
    )
    subject_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id"), nullable=True,
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    # Timing
    time_limit_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    available_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    available_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Attempts
    max_attempts: Mapped[int] = mapped_column(Integer, default=1)
    scoring_policy: Mapped[str] = mapped_column(String(20), default="highest")

    # Scoring
    passing_score: Mapped[float] = mapped_column(Float, default=50.0)
    total_points: Mapped[float] = mapped_column(Float, default=0.0)
    score_release_policy: Mapped[str] = mapped_column(String(30), default="immediate")

    # Shuffle
    shuffle_questions: Mapped[bool] = mapped_column(Boolean, default=False)
    shuffle_options: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Proctoring ──
    enforce_fullscreen: Mapped[bool] = mapped_column(Boolean, default=False)
    max_violations: Mapped[int] = mapped_column(Integer, default=3)
    time_penalty_minutes: Mapped[int] = mapped_column(Integer, default=0)
    block_keyboard_shortcuts: Mapped[bool] = mapped_column(Boolean, default=False)
    tab_switch_detection: Mapped[bool] = mapped_column(Boolean, default=True)
    devtools_detection: Mapped[bool] = mapped_column(Boolean, default=True)
    right_click_block: Mapped[bool] = mapped_column(Boolean, default=True)
    copy_paste_block: Mapped[bool] = mapped_column(Boolean, default=True)
    webcam_proctoring: Mapped[bool] = mapped_column(Boolean, default=False)

    # Access
    access_token: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, default=uuid.uuid4,
    )
    password_protected: Mapped[bool] = mapped_column(Boolean, default=False)
    access_password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # State
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ──
    group: Mapped[Optional["Group"]] = relationship(back_populates="assessments")
    curriculum_subject: Mapped[Optional["Subject"]] = relationship(back_populates="assessments")
    teacher: Mapped["User"] = relationship(back_populates="created_assessments", foreign_keys=[teacher_id])
    questions: Mapped[list["Question"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan",
    )
    attempts: Mapped[list["AssessmentAttempt"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan",
    )
    violations: Mapped[list["Violation"]] = relationship(back_populates="assessment")

    def __repr__(self) -> str:
        return f"<Assessment {self.title}>"
