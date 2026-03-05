"""
EduTrack — Student Answer Model
Stores response data for every question type.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.assessment_attempt import AssessmentAttempt
    from app.models.question import Question


class StudentAnswer(Base):
    __tablename__ = "student_answers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assessment_attempts.id"))
    question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("questions.id"))

    # Text-based answers
    answer_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # MCQ / True-False
    selected_option_ids: Mapped[Optional[list[uuid.UUID]]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True,
    )

    # Matching
    matched_pairs: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Ordering
    ordered_ids: Mapped[Optional[list[uuid.UUID]]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True,
    )

    # Categorization
    categorized: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Hotspot
    hotspot_coords: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Code
    code_submission: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Numeric
    numeric_answer: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Likert
    likert_value: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # File upload
    file_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Flags & timing
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    time_spent_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Grading
    score_awarded: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    auto_graded: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    teacher_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamp
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ──
    attempt: Mapped["AssessmentAttempt"] = relationship(back_populates="answers")
    question: Mapped["Question"] = relationship(back_populates="student_answers")

    def __repr__(self) -> str:
        return f"<StudentAnswer q={self.question_id}>"
