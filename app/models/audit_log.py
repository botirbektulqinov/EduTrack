"""
EduTrack — Audit Log Model
Immutable log of all sensitive actions.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id = Column(UUID(as_uuid=True), nullable=True)  # Nullable for system actions
    actor_role = Column(String(20), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    target_type = Column(String(50), nullable=True)
    target_id = Column(UUID(as_uuid=True), nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=True)  # renamed to avoid Python reserved word
    ip_address = Column(INET, nullable=True)
    occurred_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    def __repr__(self):
        return f"<AuditLog {self.action} by={self.actor_id}>"
