"""
EduTrack - Curriculum Subject Model
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.assessment import Assessment
    from app.models.curriculum_module import CurriculumModule
    from app.models.group import Group


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    modules: Mapped[list["CurriculumModule"]] = relationship(
        back_populates="subject",
        cascade="all, delete-orphan",
        order_by="CurriculumModule.order_index",
    )
    assessments: Mapped[list["Assessment"]] = relationship(back_populates="curriculum_subject")
    groups: Mapped[list["Group"]] = relationship(back_populates="curriculum_subject")

    def __repr__(self) -> str:
        return f"<Subject {self.name}>"
