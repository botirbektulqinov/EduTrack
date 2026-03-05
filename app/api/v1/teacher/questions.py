"""
EduTrack — Teacher: Question Management API
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_teacher_user
from app.models.user import User
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.assessment import Assessment
from app.schemas.question import (
    QuestionCreate,
    QuestionOptionCreate,
    QuestionResponse,
    QuestionUpdate,
)
from app.schemas.common import MessageResponse, SuccessResponse

router = APIRouter(tags=["Teacher - Questions"])


@router.post("/assessments/{assessment_id}/questions", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def add_question(
    assessment_id: UUID,
    data: QuestionCreate,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(get_teacher_user),
):
    """Add a question to an assessment."""
    # Verify ownership
    result = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=404, detail={"code": "ASSESSMENT_NOT_FOUND", "message": "Assessment not found."})
    if teacher.role != "admin" and assessment.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail={"code": "AUTH_INSUFFICIENT_PERMISSIONS", "message": "Not your assessment."})

    question = Question(
        assessment_id=assessment_id,
        question_type=data.question_type,
        content=data.content,
        explanation=data.explanation,
        image_url=data.image_url,
        audio_url=data.audio_url,
        video_url=data.video_url,
        points=data.points,
        partial_scoring=data.partial_scoring,
        negative_marking=data.negative_marking,
        order_index=data.order_index,
        topic_tag=data.topic_tag,
        difficulty=data.difficulty,
        blooms_level=data.blooms_level,
        time_suggestion_seconds=data.time_suggestion_seconds,
        config=data.config,
    )
    db.add(question)
    await db.flush()

    # Add options
    for opt_data in data.options:
        option = QuestionOption(
            question_id=question.id,
            content=opt_data.content,
            is_correct=opt_data.is_correct,
            match_key=opt_data.match_key,
            category_key=opt_data.category_key,
            order_position=opt_data.order_position,
            image_url=opt_data.image_url,
        )
        db.add(option)

    await db.flush()
    await db.refresh(question)

    # Reload with options
    result = await db.execute(
        select(Question).options(selectinload(Question.options)).where(Question.id == question.id)
    )
    question = result.scalar_one()

    return SuccessResponse(data=QuestionResponse.model_validate(question))


@router.patch("/questions/{question_id}", response_model=SuccessResponse)
async def update_question(
    question_id: UUID,
    data: QuestionUpdate,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(get_teacher_user),
):
    """Update a question."""
    result = await db.execute(
        select(Question).options(selectinload(Question.options)).where(Question.id == question_id)
    )
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail={"code": "QUESTION_NOT_FOUND", "message": "Question not found."})

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(question, field, value)

    await db.flush()
    await db.refresh(question)
    return SuccessResponse(data=QuestionResponse.model_validate(question))


@router.delete("/questions/{question_id}", response_model=MessageResponse)
async def delete_question(
    question_id: UUID,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(get_teacher_user),
):
    """Delete a question."""
    result = await db.execute(select(Question).where(Question.id == question_id))
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail={"code": "QUESTION_NOT_FOUND", "message": "Question not found."})

    await db.delete(question)
    await db.flush()
    return MessageResponse(message="Question deleted.")
