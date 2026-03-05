"""
EduTrack — Violation Model
Proctoring violation log entries.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


VIOLATION_TYPES = [
    "FULLSCREEN_EXIT",
    "TAB_SWITCH",
    "WINDOW_FOCUS_LOST",
    "ALT_TAB",
    "DEVTOOLS_DETECTED",
    "F11_PRESSED",
    "F12_PRESSED",
    "ESCAPE_PRESSED",
    "BLOCKED_SHORTCUT",
    "RIGHT_CLICK",
    "COPY_PASTE",
    "API_MANIPULATION",
    "EXTENSION_DETECTED",
    "SCRIPT_INJECTION",
]


class Violation(Base):
    __tablename__ = "violations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id = Column(UUID(as_uuid=True), ForeignKey("assessment_attempts.id"), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("assessments.id"), nullable=False)

    violation_type = Column(String(50), nullable=False)
    occurred_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    time_remaining_at_event = Column(Integer, nullable=True)
    time_deducted_seconds = Column(Integer, nullable=True)
    violation_count_after = Column(Integer, nullable=False)

    browser_info = Column(JSONB, nullable=True)
    ip_address = Column(INET, nullable=True)
    resolved = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)

    # Relationships
    attempt = relationship("AssessmentAttempt", back_populates="violations")
    student = relationship("User", back_populates="violations", foreign_keys=[student_id])
    assessment = relationship("Assessment", back_populates="violations")

    def __repr__(self):
        return f"<Violation {self.violation_type} count={self.violation_count_after}>"
