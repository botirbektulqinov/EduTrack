"""
EduTrack — Question Model
Supports 16 question types as per technical documentation.
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
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


# All supported question types
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

DIFFICULTY_LEVELS = ["easy", "medium", "hard"]

BLOOMS_LEVELS = [
    "remember",
    "understand",
    "apply",
    "analyze",
    "evaluate",
    "create",
]


class Question(Base):
    __tablename__ = "questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=True)
    question_bank_id = Column(UUID(as_uuid=True), ForeignKey("question_banks.id"), nullable=True)

    question_type = Column(String(30), nullable=False)  # see QUESTION_TYPES
    content = Column(Text, nullable=False)  # HTML / Markdown / LaTeX
    explanation = Column(Text, nullable=True)  # Shown after grading

    # Media
    image_url = Column(String(500), nullable=True)
    audio_url = Column(String(500), nullable=True)
    video_url = Column(String(500), nullable=True)

    # Scoring
    points = Column(Float, default=1.0, nullable=False)
    partial_scoring = Column(Boolean, default=False, nullable=False)
    negative_marking = Column(Float, default=0.0, nullable=False)

    # Ordering & metadata
    order_index = Column(Integer, nullable=True)
    topic_tag = Column(String(100), nullable=True, index=True)
    difficulty = Column(String(10), nullable=True)  # easy, medium, hard
    blooms_level = Column(String(20), nullable=True)
    time_suggestion_seconds = Column(Integer, nullable=True)

    # Type-specific config (flexible JSONB)
    config = Column(JSONB, nullable=True)
    # Examples:
    # fill_blank: {"blanks": [{"accepted_answers": ["photosynthesis"], "case_sensitive": false}]}
    # numeric: {"correct_value": 9.81, "tolerance": 0.01, "unit": "m/s²"}
    # code: {"language": "python", "test_cases": [...], "time_limit_ms": 5000, "memory_limit_mb": 256}
    # hotspot: {"zones": [{"type": "circle", "cx": 150, "cy": 200, "r": 30}]}
    # matching: {"allow_reuse": false}
    # likert: {"scale_min": 1, "scale_max": 5, "labels": ["Strongly Disagree", ..., "Strongly Agree"]}

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    assessment = relationship("Assessment", back_populates="questions")
    question_bank = relationship("QuestionBank", back_populates="questions")
    options = relationship("QuestionOption", back_populates="question", cascade="all, delete-orphan", order_by="QuestionOption.order_position")
    student_answers = relationship("StudentAnswer", back_populates="question")

    def __repr__(self):
        return f"<Question {self.question_type} pts={self.points}>"
