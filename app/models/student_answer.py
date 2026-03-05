"""
EduTrack — Student Answer Model
Stores student responses for each question in an attempt.
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
    Text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship

from app.core.database import Base


class StudentAnswer(Base):
    __tablename__ = "student_answers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id = Column(UUID(as_uuid=True), ForeignKey("assessment_attempts.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id"), nullable=False)

    # Answer data (varies by question type)
    answer_text = Column(Text, nullable=True)                     # For open types (short_answer, essay)
    selected_option_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)  # For MCQ types
    matched_pairs = Column(JSONB, nullable=True)                  # For matching: {"premise_id": "response_id", ...}
    ordered_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)  # For ordering
    categorized = Column(JSONB, nullable=True)                    # For categorization: {"category": ["item_id", ...]}
    hotspot_coords = Column(JSONB, nullable=True)                 # For hotspot: {x, y} or [{x, y}, ...]
    code_submission = Column(Text, nullable=True)                 # For code type
    numeric_answer = Column(Float, nullable=True)                 # For numeric type
    likert_value = Column(Integer, nullable=True)                 # For likert type
    file_url = Column(Text, nullable=True)                        # For audio_video / essay attachments

    # Flags
    is_flagged = Column(Boolean, default=False, nullable=False)
    time_spent_seconds = Column(Integer, nullable=True)

    # Grading
    score_awarded = Column(Float, nullable=True)
    auto_graded = Column(Boolean, default=False, nullable=False)
    teacher_feedback = Column(Text, nullable=True)

    saved_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    attempt = relationship("AssessmentAttempt", back_populates="answers")
    question = relationship("Question", back_populates="student_answers")

    def __repr__(self):
        return f"<StudentAnswer q={self.question_id} score={self.score_awarded}>"
