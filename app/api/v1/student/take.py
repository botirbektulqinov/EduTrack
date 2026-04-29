"""
EduTrack — Student: Assessment Taking API
Token validation, attempt start, answer save, submit.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.config import settings
from app.core.rate_limit import RateLimit, check_user_rate_limit
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
    CodeRunRequest,
    CodeRunResponse,
)
from app.schemas.question import QuestionStudentView, QuestionOptionStudentView
from app.schemas.common import MessageResponse, SuccessResponse
from app.services.attempt_service import (
    ANSWER_MUTABLE_FIELDS,
    ensure_attempt_in_progress,
    lock_attempt_start_slot,
    reject_if_time_expired,
    sync_attempt_timer,
    utc_now,
    validate_questions_belong_to_attempt,
)
from app.services.assessment_service import AssessmentService
from app.services.grading_service import GradingService
from app.services.link_service import LinkService

router = APIRouter(tags=["Student - Take Assessment"])


def _apply_answer_payload(answer: StudentAnswer, answer_data: AnswerSaveRequest) -> None:
    for field in ANSWER_MUTABLE_FIELDS:
        value = getattr(answer_data, field, None)
        if value is not None:
            setattr(answer, field, value)
    answer.saved_at = utc_now()


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
    await check_user_rate_limit(
        student.id,
        RateLimit("assessment-start", settings.RATE_LIMIT_ASSESSMENT_START_PER_MINUTE, 60),
    )
    assessment = await AssessmentService.get_assessment_by_token(db, token)
    if assessment:
        await lock_attempt_start_slot(db, assessment_id=assessment.id, student_id=student.id)
        ok, reason = await AssessmentService.validate_student_access(db, assessment, student.id)
        if not ok:
            assessment = None
    else:
        reason = "ASSESSMENT_TOKEN_INVALID"
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

        # Sanitize config for student view (remove answer keys / hidden cases)
        safe_config = None
        if q.config:
            safe_config = {
                k: v for k, v in q.config.items()
                if k not in (
                    "accepted_answers",
                    "correct_value",
                    "zones",
                    "hidden_test_cases",
                    "test_cases",
                )
            }
            if q.question_type == "likert":
                safe_config = q.config  # Likert config is fully visible
            if q.question_type == "numeric":
                safe_config = {"unit": q.config.get("unit")}
            if q.question_type == "fill_blank":
                safe_config = {"blank_count": len(q.config.get("blanks", []))}
            if q.question_type == "code":
                visible_test_cases = q.config.get("visible_test_cases")
                if visible_test_cases is None:
                    visible_test_cases = [
                        {
                            "input": test_case.get("input", ""),
                            "output": test_case.get("output", ""),
                        }
                        for test_case in q.config.get("test_cases", [])
                        if not test_case.get("is_hidden")
                    ]

                safe_config = {
                    "language": q.config.get("language", "python"),
                    "execution_mode": q.config.get("execution_mode", "stdin_stdout"),
                    "function_name": q.config.get("function_name"),
                    "starter_code": q.config.get("starter_code"),
                    "visible_test_cases": visible_test_cases or [],
                    "time_limit_seconds": q.config.get("time_limit_seconds", 2),
                    "memory_limit_mb": q.config.get("memory_limit_mb"),
                }

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
    await check_user_rate_limit(
        student.id,
        RateLimit("answer-save", settings.RATE_LIMIT_ANSWER_SAVE_PER_MINUTE, 60),
    )
    result = await db.execute(
        select(AssessmentAttempt).where(
            AssessmentAttempt.id == attempt_id,
            AssessmentAttempt.student_id == student.id,
        ).with_for_update()
    )
    attempt = result.scalar_one_or_none()
    if not attempt:
        raise HTTPException(status_code=404, detail={"code": "ATTEMPT_NOT_FOUND", "message": "Attempt not found."})
    ensure_attempt_in_progress(attempt)
    await reject_if_time_expired(db, attempt)

    incoming_by_question = {answer.question_id: answer for answer in data.answers}
    question_ids = set(incoming_by_question)
    await validate_questions_belong_to_attempt(db, attempt, question_ids)

    existing_answers = {}
    if question_ids:
        existing_result = await db.execute(
            select(StudentAnswer).where(
                StudentAnswer.attempt_id == attempt_id,
                StudentAnswer.question_id.in_(question_ids),
            )
        )
        existing_answers = {
            answer.question_id: answer
            for answer in existing_result.scalars().all()
        }

    for question_id, answer_data in incoming_by_question.items():
        answer = existing_answers.get(question_id)

        if answer:
            _apply_answer_payload(answer, answer_data)
        else:
            answer = StudentAnswer(
                attempt_id=attempt_id,
                question_id=question_id,
            )
            _apply_answer_payload(answer, answer_data)
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
        ).with_for_update()
    )
    attempt = result.scalar_one_or_none()
    if not attempt:
        raise HTTPException(status_code=404, detail={"code": "ATTEMPT_NOT_FOUND", "message": "Attempt not found."})
    if attempt.status != "in_progress":
        raise HTTPException(status_code=409, detail={"code": "ATTEMPT_ALREADY_SUBMITTED", "message": "Already submitted or terminated."})

    await sync_attempt_timer(db, attempt)
    attempt.status = "submitted"
    attempt.submitted_at = utc_now()
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


@router.post("/attempts/{attempt_id}/questions/{question_id}/run-code", response_model=SuccessResponse)
async def run_code_preview(
    attempt_id: UUID,
    question_id: UUID,
    data: CodeRunRequest,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(get_student_user),
):
    """Execute a code answer against visible test cases before final submission."""
    await check_user_rate_limit(
        student.id,
        RateLimit("code-preview", settings.RATE_LIMIT_CODE_PREVIEW_PER_MINUTE, 60),
    )
    attempt = (
        await db.execute(
            select(AssessmentAttempt)
            .options(selectinload(AssessmentAttempt.assessment))
            .where(
                AssessmentAttempt.id == attempt_id,
                AssessmentAttempt.student_id == student.id,
            )
        )
    ).scalar_one_or_none()
    if not attempt:
        raise HTTPException(
            status_code=404,
            detail={"code": "ATTEMPT_NOT_FOUND", "message": "Attempt not found."},
        )
    if attempt.status != "in_progress":
        raise HTTPException(
            status_code=409,
            detail={"code": "ATTEMPT_NOT_ACTIVE", "message": "Code preview is only available during an active attempt."},
        )

    question = (
        await db.execute(
            select(Question)
            .options(selectinload(Question.options))
            .where(
                Question.id == question_id,
                Question.assessment_id == attempt.assessment_id,
            )
        )
    ).scalar_one_or_none()
    if not question or question.question_type != "code":
        raise HTTPException(
            status_code=404,
            detail={"code": "QUESTION_NOT_FOUND", "message": "Coding question not found for this attempt."},
        )

    grading_service = GradingService()
    try:
        result = grading_service.run_code_preview(question, data.code_submission)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "CODE_PREVIEW_UNAVAILABLE", "message": str(exc)},
        ) from exc

    return SuccessResponse(data=CodeRunResponse.model_validate(result))


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
