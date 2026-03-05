"""
EduTrack — Student: Assessment Taking API
Token validation, attempt start, answer save, submit.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_student_user
from app.models.user import User
from app.models.assessment import Assessment
from app.models.assessment_attempt import AssessmentAttempt
from app.models.student_answer import StudentAnswer
from app.models.question import Question
from app.schemas.assessment import AssessmentMetadataResponse
from app.schemas.attempt import (
    AnswerSaveRequest,
    AttemptStartResponse,
    AttemptStatusResponse,
    BulkAnswerSaveRequest,
)
from app.schemas.question import QuestionStudentView, QuestionOptionStudentView
from app.schemas.common import MessageResponse, SuccessResponse
from app.services.assessment_service import AssessmentService
from app.services.grading_service import GradingService
from app.services.link_service import LinkService

router = APIRouter(tags=["Student - Take Assessment"])


@router.get("/take/{token}", response_model=SuccessResponse)
async def validate_token(
    token: UUID,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(get_student_user),
):
    """Validate access token — returns assessment metadata (no questions)."""
    assessment, reason = await LinkService.validate_token(db, token, student.id)
    if not assessment:
        error_map = {
            "ASSESSMENT_TOKEN_INVALID": (403, "Access token invalid or expired."),
            "ASSESSMENT_NOT_PUBLISHED": (403, "Assessment not published."),
            "ASSESSMENT_DEACTIVATED": (403, "This assessment has been closed."),
            "ASSESSMENT_NOT_YET_AVAILABLE": (403, f"This assessment opens on {assessment.available_from if assessment else 'N/A'}."),
            "ASSESSMENT_EXPIRED": (403, "This assessment is no longer available."),
            "STUDENT_NOT_IN_GROUP": (403, "You are not authorized for this assessment."),
            "ASSESSMENT_MAX_ATTEMPTS": (403, "You have used all available attempts."),
        }
        code, msg = error_map.get(reason, (403, reason))
        raise HTTPException(status_code=code, detail={"code": reason, "message": msg})

    question_count = len(assessment.questions) if assessment.questions else 0
    metadata = AssessmentMetadataResponse(
        title=assessment.title,
        description=assessment.description,
        assessment_type=assessment.assessment_type,
        time_limit_minutes=assessment.time_limit_minutes,
        question_count=question_count,
        enforce_fullscreen=assessment.enforce_fullscreen,
        max_violations=assessment.max_violations,
        available_from=assessment.available_from,
        available_until=assessment.available_until,
    )
    return SuccessResponse(data=metadata)


@router.post("/take/{token}/start", response_model=SuccessResponse)
async def start_attempt(
    token: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(get_student_user),
):
    """Start an assessment attempt — returns shuffled questions."""
    assessment, reason = await LinkService.validate_token(db, token, student.id)
    if not assessment:
        raise HTTPException(status_code=403, detail={"code": reason, "message": "Cannot start assessment."})

    # Calculate time limit with accommodation
    base_time = (assessment.time_limit_minutes or 0) * 60
    time_limit_seconds = int(base_time * student.extra_time_factor)

    # Create attempt
    attempt = AssessmentAttempt(
        assessment_id=assessment.id,
        student_id=student.id,
        status="in_progress",
        time_limit_seconds=time_limit_seconds,
        time_remaining_seconds=time_limit_seconds,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(attempt)
    await db.flush()
    await db.refresh(attempt)

    # Get shuffled questions (using attempt ID as seed for reproducibility)
    questions = AssessmentService.get_shuffled_questions(assessment, seed=hash(str(attempt.id)))

    # Build student-safe question views (no correct answers)
    question_views = []
    for q in questions:
        options = [
            QuestionOptionStudentView(
                id=opt.id,
                content=opt.content,
                match_key=opt.match_key,
                category_key=opt.category_key,
                image_url=opt.image_url,
            )
            for opt in q.options
        ]
        # Shuffle options if configured
        if assessment.shuffle_options:
            import random
            rng = random.Random(hash(str(attempt.id) + str(q.id)))
            rng.shuffle(options)

        # Sanitize config for student view (remove correct answers from config)
        safe_config = None
        if q.config:
            safe_config = {k: v for k, v in q.config.items() if k not in ("accepted_answers", "correct_value", "zones")}
            if q.question_type == "likert":
                safe_config = q.config  # Likert config is fully visible
            if q.question_type == "numeric":
                safe_config = {"unit": q.config.get("unit")}
            if q.question_type == "fill_blank":
                safe_config = {"blank_count": len(q.config.get("blanks", []))}

        question_views.append(QuestionStudentView(
            id=q.id,
            question_type=q.question_type,
            content=q.content,
            image_url=q.image_url,
            audio_url=q.audio_url,
            video_url=q.video_url,
            points=q.points,
            order_index=q.order_index,
            time_suggestion_seconds=q.time_suggestion_seconds,
            config=safe_config,
            options=options,
        ))

    return SuccessResponse(data=AttemptStartResponse(
        attempt_id=attempt.id,
        server_token=attempt.server_token,
        time_limit_seconds=time_limit_seconds,
        questions=[qv.model_dump() for qv in question_views],
    ))


@router.post("/attempts/{attempt_id}/save", response_model=MessageResponse)
async def save_answers(
    attempt_id: UUID,
    data: BulkAnswerSaveRequest,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(get_student_user),
):
    """Auto-save answers (partial, can be called repeatedly)."""
    result = await db.execute(
        select(AssessmentAttempt).where(
            AssessmentAttempt.id == attempt_id,
            AssessmentAttempt.student_id == student.id,
        )
    )
    attempt = result.scalar_one_or_none()
    if not attempt:
        raise HTTPException(status_code=404, detail={"code": "ATTEMPT_NOT_FOUND", "message": "Attempt not found."})
    if attempt.status not in ("in_progress",):
        raise HTTPException(status_code=409, detail={"code": "ATTEMPT_ALREADY_SUBMITTED", "message": "Cannot save to a submitted/terminated attempt."})

    for answer_data in data.answers:
        # Upsert: check existing answer for this question
        existing = await db.execute(
            select(StudentAnswer).where(
                StudentAnswer.attempt_id == attempt_id,
                StudentAnswer.question_id == answer_data.question_id,
            )
        )
        answer = existing.scalar_one_or_none()

        if answer:
            # Update existing
            for field in ("answer_text", "selected_option_ids", "matched_pairs", "ordered_ids",
                          "categorized", "hotspot_coords", "code_submission", "numeric_answer",
                          "likert_value", "is_flagged", "time_spent_seconds"):
                val = getattr(answer_data, field, None)
                if val is not None:
                    setattr(answer, field, val)
            answer.saved_at = datetime.now(timezone.utc)
        else:
            # Create new
            answer = StudentAnswer(
                attempt_id=attempt_id,
                question_id=answer_data.question_id,
                answer_text=answer_data.answer_text,
                selected_option_ids=answer_data.selected_option_ids,
                matched_pairs=answer_data.matched_pairs,
                ordered_ids=answer_data.ordered_ids,
                categorized=answer_data.categorized,
                hotspot_coords=answer_data.hotspot_coords,
                code_submission=answer_data.code_submission,
                numeric_answer=answer_data.numeric_answer,
                likert_value=answer_data.likert_value,
                is_flagged=answer_data.is_flagged,
                time_spent_seconds=answer_data.time_spent_seconds,
            )
            db.add(answer)

    await db.flush()
    return MessageResponse(message="Answers saved.")


@router.post("/attempts/{attempt_id}/submit", response_model=SuccessResponse)
async def submit_attempt(
    attempt_id: UUID,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(get_student_user),
):
    """Final submission of an assessment attempt. Triggers auto-grading."""
    result = await db.execute(
        select(AssessmentAttempt).where(
            AssessmentAttempt.id == attempt_id,
            AssessmentAttempt.student_id == student.id,
        )
    )
    attempt = result.scalar_one_or_none()
    if not attempt:
        raise HTTPException(status_code=404, detail={"code": "ATTEMPT_NOT_FOUND", "message": "Attempt not found."})
    if attempt.status not in ("in_progress",):
        raise HTTPException(status_code=409, detail={"code": "ATTEMPT_ALREADY_SUBMITTED", "message": "Already submitted or terminated."})

    attempt.status = "submitted"
    attempt.submitted_at = datetime.now(timezone.utc)
    await db.flush()

    # Auto-grade
    grading_service = GradingService()
    grading_result = await grading_service.grade_attempt(db, attempt)

    return SuccessResponse(data={
        "attempt_id": str(attempt.id),
        "status": attempt.status,
        "score_percent": grading_result["score_percent"],
        "grade": grading_result["grade"],
        "needs_manual_review": grading_result["needs_manual_review"],
    })


@router.get("/attempts/{attempt_id}/result", response_model=SuccessResponse)
async def get_result(
    attempt_id: UUID,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(get_student_user),
):
    """Get result of an attempt (if released)."""
    result = await db.execute(
        select(AssessmentAttempt)
        .options(selectinload(AssessmentAttempt.answers))
        .where(
            AssessmentAttempt.id == attempt_id,
            AssessmentAttempt.student_id == student.id,
        )
    )
    attempt = result.scalar_one_or_none()
    if not attempt:
        raise HTTPException(status_code=404, detail={"code": "ATTEMPT_NOT_FOUND", "message": "Attempt not found."})

    if attempt.status in ("in_progress", "not_started"):
        raise HTTPException(status_code=403, detail={"code": "RESULT_NOT_AVAILABLE", "message": "Assessment not yet submitted."})

    # Check release policy
    assessment_result = await db.execute(select(Assessment).where(Assessment.id == attempt.assessment_id))
    assessment = assessment_result.scalar_one()

    if assessment.score_release_policy == "after_review" and attempt.status != "graded":
        return SuccessResponse(data={
            "attempt_id": str(attempt.id),
            "status": attempt.status,
            "message": "Results pending teacher review.",
        })

    return SuccessResponse(data=AttemptStatusResponse.model_validate(attempt))
