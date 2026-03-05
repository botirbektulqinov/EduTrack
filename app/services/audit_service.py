"""
EduTrack — Audit Service
Immutable logging of all sensitive actions.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditService:

    @staticmethod
    async def log(
        db: AsyncSession,
        action: str,
        actor_id: Optional[UUID] = None,
        actor_role: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[UUID] = None,
        metadata: Optional[dict] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        entry = AuditLog(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata_=metadata,
            ip_address=ip_address,
        )
        db.add(entry)
        await db.flush()
        return entry
