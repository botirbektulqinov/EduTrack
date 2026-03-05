"""
EduTrack — Performance Snapshot Model
Periodic snapshots of student performance for analytics.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.group import Group
    from app.models.user import User


class PerformanceSnapshot(Base):
    __tablename__ = "performance_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=True,
    )
    period_type: Mapped[str] = mapped_column(String(20))  # weekly, monthly, semester
    period_label: Mapped[str] = mapped_column(String(50))
    assessments_taken: Mapped[int] = mapped_column(Integer, default=0)
    assessments_passed: Mapped[int] = mapped_column(Integer, default=0)
    avg_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    best_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    worst_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    improvement_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    violation_total: Mapped[int] = mapped_column(Integer, default=0)
    at_risk: Mapped[bool] = mapped_column(Boolean, default=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ──
    student: Mapped["User"] = relationship(back_populates="performance_snapshots")
    group: Mapped[Optional["Group"]] = relationship()

    def __repr__(self) -> str:
        return f"<PerformanceSnapshot student={self.student_id} period={self.period_label}>"
