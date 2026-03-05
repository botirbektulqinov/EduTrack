"""
EduTrack — Assessment Attempt Model
Tracks each student attempt with timing, scoring, and proctoring data.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.assessment import Assessment
    from app.models.student_answer import StudentAnswer
    from app.models.user import User
    from app.models.violation import Violation


class AssessmentAttempt(Base):
    __tablename__ = "assessment_attempts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assessments.id"))
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    # Status
    status: Mapped[str] = mapped_column(String(30), default="not_started")

    # Timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    time_limit_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    time_remaining_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Scoring
    score_raw: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    score_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    grade: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)

    # Proctoring
    violation_count: Mapped[int] = mapped_column(Integer, default=0)
    termination_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Security
    server_token: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid.uuid4,
    )
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ──
    assessment: Mapped["Assessment"] = relationship(back_populates="attempts")
    student: Mapped["User"] = relationship(back_populates="assessment_attempts")
    answers: Mapped[list["StudentAnswer"]] = relationship(
        back_populates="attempt", cascade="all, delete-orphan",
    )
    violations: Mapped[list["Violation"]] = relationship(
        back_populates="attempt", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Attempt {self.id} status={self.status}>"
