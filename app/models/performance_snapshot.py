"""
EduTrack — Performance Snapshot Model
Materialized performance data, updated periodically by Celery.
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
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class PerformanceSnapshot(Base):
    __tablename__ = "performance_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=True)

    period_type = Column(String(20), nullable=False)   # semester, year, all_time
    period_label = Column(String(50), nullable=True)    # e.g., "2025-2026 Fall"

    assessments_taken = Column(Integer, default=0, nullable=False)
    assessments_passed = Column(Integer, default=0, nullable=False)
    avg_score = Column(Float, nullable=True)
    best_score = Column(Float, nullable=True)
    worst_score = Column(Float, nullable=True)
    improvement_rate = Column(Float, nullable=True)     # regression slope
    violation_total = Column(Integer, default=0, nullable=False)
    at_risk = Column(Boolean, default=False, nullable=False)

    computed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    student = relationship("User", back_populates="performance_snapshots", foreign_keys=[student_id])

    def __repr__(self):
        return f"<PerformanceSnapshot student={self.student_id} avg={self.avg_score}>"
