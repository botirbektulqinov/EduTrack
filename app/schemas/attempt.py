"""
EduTrack — Attempt & Answer Schemas
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


# ── Student Answer Response ──

class StudentAnswerResponse(BaseModel):
    id: UUID
    question_id: UUID
    answer_text: Optional[str] = None
    selected_option_ids: Optional[List[UUID]] = None
    matched_pairs: Optional[Dict[str, Any]] = None
    ordered_ids: Optional[List[UUID]] = None
    categorized: Optional[Dict[str, Any]] = None
    hotspot_coords: Optional[Any] = None
    code_submission: Optional[str] = None
    numeric_answer: Optional[float] = None
    likert_value: Optional[int] = None
    file_url: Optional[str] = None
    is_flagged: bool = False
    time_spent_seconds: Optional[int] = None
    score_awarded: Optional[float] = None
    auto_graded: Optional[bool] = None
    teacher_feedback: Optional[str] = None
    saved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Violation Response ──

class ViolationResponse(BaseModel):
    id: UUID
    violation_type: str
    occurred_at: datetime
    time_remaining_at_event: Optional[int] = None
    time_deducted_seconds: int = 0
    violation_count_after: int = 0
    resolved: bool = False
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Attempt ──

class AttemptStartResponse(BaseModel):
    attempt_id: UUID
    server_token: UUID
    time_limit_seconds: int
    questions: List[Any]  # List[QuestionStudentView]


class AttemptStatusResponse(BaseModel):
    id: UUID
    assessment_id: UUID
    status: str
    started_at: datetime
    submitted_at: Optional[datetime]
    time_remaining_seconds: Optional[int]
    violation_count: int
    score_raw: Optional[float]
    score_percent: Optional[float]
    grade: Optional[str]

    model_config = {"from_attributes": True}


class AttemptDetailResponse(AttemptStatusResponse):
    student_name: Optional[str] = None
    assessment_title: Optional[str] = None
    answers: List[StudentAnswerResponse] = []
    violations: List[ViolationResponse] = []
    questions: List[Any] = []


class AttemptListResponse(BaseModel):
    id: UUID
    assessment_id: UUID
    student_id: UUID
    student_name: Optional[str] = None
    assessment_title: Optional[str] = None
    status: str
    started_at: datetime
    submitted_at: Optional[datetime]
    score_percent: Optional[float]
    grade: Optional[str]
    violation_count: int

    model_config = {"from_attributes": True}


# ── Answer Save ──

class AnswerSaveRequest(BaseModel):
    question_id: UUID
    answer_text: Optional[str] = None
    selected_option_ids: Optional[List[UUID]] = None
    matched_pairs: Optional[Dict[str, str]] = None
    ordered_ids: Optional[List[UUID]] = None
    categorized: Optional[Dict[str, List[str]]] = None
    hotspot_coords: Optional[Any] = None
    code_submission: Optional[str] = None
    numeric_answer: Optional[float] = None
    likert_value: Optional[int] = None
    is_flagged: bool = False
    time_spent_seconds: Optional[int] = None


class BulkAnswerSaveRequest(BaseModel):
    answers: List[AnswerSaveRequest]


# ── Grading ──

class ManualGradeRequest(BaseModel):
    question_id: UUID
    score_awarded: float
    teacher_feedback: Optional[str] = None


class BulkManualGradeRequest(BaseModel):
    grades: List[ManualGradeRequest]


# ── Result ──

class ResultResponse(BaseModel):
    attempt_id: UUID
    assessment_title: str
    assessment_type: str
    status: str
    started_at: datetime
    submitted_at: Optional[datetime]
    score_raw: Optional[float]
    score_percent: Optional[float]
    grade: Optional[str]
    total_points: float
    violation_count: int


class ResultDetailResponse(ResultResponse):
    answers: List[StudentAnswerResponse] = []  # with question content and feedback
