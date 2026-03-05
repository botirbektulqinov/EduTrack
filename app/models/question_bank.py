"""
EduTrack — Question Bank Model
Per-teacher reusable repository of questions.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class QuestionBank(Base):
    __tablename__ = "question_banks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    subject = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    questions = relationship("Question", back_populates="question_bank")

    def __repr__(self):
        return f"<QuestionBank {self.name}>"
