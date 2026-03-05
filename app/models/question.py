"""
EduTrack — Question Model
Supports 16 question types (see QUESTION_TYPES).
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.assessment import Assessment
    from app.models.question_bank import QuestionBank
    from app.models.question_option import QuestionOption
    from app.models.student_answer import StudentAnswer


QUESTION_TYPES = [
    "true_false",       # TYPE-01
    "yes_no",           # TYPE-02
    "mcq_single",       # TYPE-03
    "mcq_multi",        # TYPE-04
    "image_mcq",        # TYPE-05
    "short_answer",     # TYPE-06
    "essay",            # TYPE-07
    "fill_blank",       # TYPE-08
    "numeric",          # TYPE-09
    "matching",         # TYPE-10
    "ordering",         # TYPE-11
    "categorization",   # TYPE-12
    "hotspot",          # TYPE-13
    "code",             # TYPE-14
    "audio_video",      # TYPE-15
    "likert",           # TYPE-16
]


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assessments.id"), nullable=True,
    )
    question_bank_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("question_banks.id"), nullable=True,
    )
    question_type: Mapped[str] = mapped_column(String(30))

    # Content
    content: Mapped[str] = mapped_column(Text)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    audio_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    video_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Scoring
    points: Mapped[float] = mapped_column(Float, default=1.0)
    partial_scoring: Mapped[bool] = mapped_column(Boolean, default=False)
    negative_marking: Mapped[float] = mapped_column(Float, default=0.0)

    # Ordering / metadata
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    topic_tag: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    difficulty: Mapped[str] = mapped_column(String(20), default="medium")
    blooms_level: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    time_suggestion_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Type-specific configuration (JSONB)
    config: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

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
    assessment: Mapped[Optional["Assessment"]] = relationship(back_populates="questions")
    question_bank: Mapped[Optional["QuestionBank"]] = relationship(back_populates="questions")
    options: Mapped[list["QuestionOption"]] = relationship(
        back_populates="question", cascade="all, delete-orphan",
    )
    student_answers: Mapped[list["StudentAnswer"]] = relationship(back_populates="question")

    def __repr__(self) -> str:
        return f"<Question {self.question_type}: {self.content[:40]}>"
