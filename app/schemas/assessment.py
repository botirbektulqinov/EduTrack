"""
EduTrack — Assessment Schemas
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.question import QuestionResponse


class ProctoringSettings(BaseModel):
    enforce_fullscreen: bool = True
    max_violations: int = 3
    time_penalty_minutes: int = 2
    block_keyboard_shortcuts: bool = True
    tab_switch_detection: bool = True
    devtools_detection: bool = True
    right_click_block: bool = True
    copy_paste_block: bool = True
    webcam_proctoring: bool = False


class AssessmentCreate(BaseModel):
    title: str
    description: Optional[str] = None
    assessment_type: str  # test, quiz, survey, practice
    format_type: str = "timed_test"
    group_id: Optional[UUID] = None
    subject_id: Optional[UUID] = None
    time_limit_minutes: Optional[int] = None
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None
    max_attempts: int = 1
    scoring_policy: str = "best"
    passing_score: float = 50.0
    score_release_policy: str = "immediate"
    shuffle_questions: bool = True
    shuffle_options: bool = True
    password_protected: bool = False
    access_password: Optional[str] = None
    proctoring: ProctoringSettings = ProctoringSettings()


class AssessmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assessment_type: Optional[str] = None
    format_type: Optional[str] = None
    group_id: Optional[UUID] = None
    subject_id: Optional[UUID] = None
    time_limit_minutes: Optional[int] = None
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None
    max_attempts: Optional[int] = None
    scoring_policy: Optional[str] = None
    passing_score: Optional[float] = None
    score_release_policy: Optional[str] = None
    shuffle_questions: Optional[bool] = None
    shuffle_options: Optional[bool] = None
    proctoring: Optional[ProctoringSettings] = None


class AssessmentResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    assessment_type: str
    format_type: str
    group_id: Optional[UUID]
    group_name: Optional[str] = None
    subject_id: Optional[UUID] = None
    subject_name: Optional[str] = None
    group_subject_id: Optional[UUID] = None
    group_subject_name: Optional[str] = None
    teacher_id: Optional[UUID]
    time_limit_minutes: Optional[int]
    available_from: Optional[datetime]
    available_until: Optional[datetime]
    max_attempts: int
    scoring_policy: str
    passing_score: float
    total_points: float
    score_release_policy: str
    shuffle_questions: bool
    shuffle_options: bool
    enforce_fullscreen: bool
    max_violations: int
    time_penalty_minutes: int
    block_keyboard_shortcuts: bool
    tab_switch_detection: bool
    devtools_detection: bool
    right_click_block: bool
    copy_paste_block: bool
    webcam_proctoring: bool
    access_token: UUID
    is_published: bool
    is_active: bool
    question_count: int = 0
    questions: List[QuestionResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssessmentListResponse(BaseModel):
    id: UUID
    title: str
    assessment_type: str
    group_id: Optional[UUID]
    group_name: Optional[str] = None
    subject_id: Optional[UUID] = None
    subject_name: Optional[str] = None
    group_subject_id: Optional[UUID] = None
    group_subject_name: Optional[str] = None
    time_limit_minutes: Optional[int] = None
    is_published: bool
    is_active: bool
    available_from: Optional[datetime]
    available_until: Optional[datetime]
    question_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class AssessmentMetadataResponse(BaseModel):
    """Returned when student validates a token — no questions included."""
    title: str
    description: Optional[str]
    assessment_type: str
    time_limit_minutes: Optional[int]
    question_count: int
    enforce_fullscreen: bool
    max_violations: int
    available_from: Optional[datetime]
    available_until: Optional[datetime]
