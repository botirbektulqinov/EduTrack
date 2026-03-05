"""
EduTrack — Question Option Model
For MCQ, matching, ordering, categorization question types.
"""

import uuid

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class QuestionOption(Base):
    __tablename__ = "question_options"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False, nullable=False)
    match_key = Column(String(100), nullable=True)       # For matching type
    category_key = Column(String(100), nullable=True)     # For categorization
    order_position = Column(Integer, nullable=True)       # Correct position for ordering
    image_url = Column(String(500), nullable=True)

    # Relationships
    question = relationship("Question", back_populates="options")

    def __repr__(self):
        return f"<QuestionOption correct={self.is_correct}>"
