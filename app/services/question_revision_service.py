"""
EduTrack - Question Revision Service
"""

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.question_revision import QuestionRevision


class QuestionRevisionService:

    @staticmethod
    def build_snapshot(question: Question) -> dict[str, Any]:
        return {
            "question_type": question.question_type,
            "content": question.content,
            "explanation": question.explanation,
            "image_url": question.image_url,
            "audio_url": question.audio_url,
            "video_url": question.video_url,
            "points": question.points,
            "partial_scoring": question.partial_scoring,
            "negative_marking": question.negative_marking,
            "order_index": question.order_index,
            "topic_tag": question.topic_tag,
            "topic_id": str(question.topic_id) if question.topic_id else None,
            "difficulty": question.difficulty,
            "blooms_level": question.blooms_level,
            "time_suggestion_seconds": question.time_suggestion_seconds,
            "config": question.config,
            "options": [
                {
                    "content": option.content,
                    "is_correct": option.is_correct,
                    "match_key": option.match_key,
                    "category_key": option.category_key,
                    "order_position": option.order_position,
                    "image_url": option.image_url,
                }
                for option in question.options
            ],
        }

    @staticmethod
    async def create_revision(
        db: AsyncSession,
        question_id: UUID,
        created_by_id: UUID | None,
        source: str,
        summary: str | None = None,
    ) -> QuestionRevision:
        question = (
            await db.execute(
                select(Question)
                .options(selectinload(Question.options))
                .where(Question.id == question_id)
            )
        ).scalar_one()

        version_number = (
            await db.execute(
                select(func.max(QuestionRevision.version_number))
                .where(QuestionRevision.question_id == question_id)
            )
        ).scalar() or 0

        revision = QuestionRevision(
            question_id=question_id,
            created_by_id=created_by_id,
            version_number=version_number + 1,
            source=source,
            summary=summary,
            snapshot=QuestionRevisionService.build_snapshot(question),
        )
        db.add(revision)
        await db.flush()
        return revision
