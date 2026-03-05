"""
EduTrack — Question Schemas
All 16 question types.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


class QuestionOptionCreate(BaseModel):
    content: str
    is_correct: bool = False
    match_key: Optional[str] = None
    category_key: Optional[str] = None
    order_position: Optional[int] = None
    image_url: Optional[str] = None


class QuestionOptionResponse(BaseModel):
    id: UUID
    content: str
    is_correct: bool
    match_key: Optional[str] = None
    category_key: Optional[str] = None
    order_position: Optional[int] = None
    image_url: Optional[str] = None

    model_config = {"from_attributes": True}


class QuestionOptionStudentView(BaseModel):
    """Option as shown to students (no is_correct)."""
    id: UUID
    content: str
    match_key: Optional[str] = None
    category_key: Optional[str] = None
    image_url: Optional[str] = None

    model_config = {"from_attributes": True}


class QuestionCreate(BaseModel):
    question_type: str
    content: str
    explanation: Optional[str] = None
    image_url: Optional[str] = None
    audio_url: Optional[str] = None
    video_url: Optional[str] = None
    points: float = 1.0
    partial_scoring: bool = False
    negative_marking: float = 0.0
    order_index: Optional[int] = None
    topic_tag: Optional[str] = None
    difficulty: Optional[str] = None
    blooms_level: Optional[str] = None
    time_suggestion_seconds: Optional[int] = None
    config: Optional[Dict[str, Any]] = None
    options: List[QuestionOptionCreate] = []


class QuestionUpdate(BaseModel):
    question_type: Optional[str] = None
    content: Optional[str] = None
    explanation: Optional[str] = None
    image_url: Optional[str] = None
    audio_url: Optional[str] = None
    video_url: Optional[str] = None
    points: Optional[float] = None
    partial_scoring: Optional[bool] = None
    negative_marking: Optional[float] = None
    order_index: Optional[int] = None
    topic_tag: Optional[str] = None
    difficulty: Optional[str] = None
    blooms_level: Optional[str] = None
    time_suggestion_seconds: Optional[int] = None
    config: Optional[Dict[str, Any]] = None


class QuestionResponse(BaseModel):
    id: UUID
    assessment_id: Optional[UUID]
    question_bank_id: Optional[UUID]
    question_type: str
    content: str
    explanation: Optional[str]
    image_url: Optional[str]
    audio_url: Optional[str]
    video_url: Optional[str]
    points: float
    partial_scoring: bool
    negative_marking: float
    order_index: Optional[int]
    topic_tag: Optional[str]
    difficulty: Optional[str]
    blooms_level: Optional[str]
    time_suggestion_seconds: Optional[int]
    config: Optional[Dict[str, Any]]
    options: List[QuestionOptionResponse] = []

    model_config = {"from_attributes": True}


class QuestionStudentView(BaseModel):
    """Question as shown to students (no correct answers, no explanation)."""
    id: UUID
    question_type: str
    content: str
    image_url: Optional[str]
    audio_url: Optional[str]
    video_url: Optional[str]
    points: float
    order_index: Optional[int]
    time_suggestion_seconds: Optional[int]
    config: Optional[Dict[str, Any]] = None  # Sanitized per type
    options: List[QuestionOptionStudentView] = []

    model_config = {"from_attributes": True}
