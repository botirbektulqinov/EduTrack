"""
EduTrack — Proctoring Violation Model
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.assessment import Assessment
    from app.models.assessment_attempt import AssessmentAttempt
    from app.models.user import User

VIOLATION_TYPES = [
    "FULLSCREEN_EXIT",
    "TAB_SWITCH",
    "DEVTOOLS_OPEN",
    "RIGHT_CLICK",
    "COPY_PASTE",
    "KEYBOARD_SHORTCUT",
    "WINDOW_RESIZE",
    "MULTIPLE_DISPLAYS",
    "WEBCAM_FACE_MISSING",
    "WEBCAM_MULTIPLE_FACES",
    "WEBCAM_SUSPICIOUS_OBJECT",
    "NETWORK_ANOMALY",
    "IDLE_TIMEOUT",
    "UNKNOWN",
]


class Violation(Base):
    __tablename__ = "violations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assessment_attempts.id"))
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    assessment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assessments.id"))
    violation_type: Mapped[str] = mapped_column(String(50))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    time_remaining_at_event: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    time_deducted_seconds: Mapped[int] = mapped_column(Integer, default=0)
    violation_count_after: Mapped[int] = mapped_column(Integer, default=0)
    browser_info: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Relationships ──
    attempt: Mapped["AssessmentAttempt"] = relationship(back_populates="violations")
    student: Mapped["User"] = relationship(back_populates="violations")
    assessment: Mapped["Assessment"] = relationship(back_populates="violations")

    def __repr__(self) -> str:
        return f"<Violation {self.violation_type} attempt={self.attempt_id}>"
