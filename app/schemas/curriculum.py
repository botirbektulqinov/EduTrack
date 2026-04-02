"""
EduTrack - Curriculum Schemas
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class SubjectCreate(BaseModel):
    name: str
    code: Optional[str] = None
    description: Optional[str] = None


class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None


class CurriculumModuleCreate(BaseModel):
    subject_id: UUID
    name: str
    description: Optional[str] = None
    order_index: int = 0


class CurriculumModuleUpdate(BaseModel):
    subject_id: Optional[UUID] = None
    name: Optional[str] = None
    description: Optional[str] = None
    order_index: Optional[int] = None


class TopicCreate(BaseModel):
    module_id: UUID
    name: str
    description: Optional[str] = None
    order_index: int = 0


class TopicUpdate(BaseModel):
    module_id: Optional[UUID] = None
    name: Optional[str] = None
    description: Optional[str] = None
    order_index: Optional[int] = None


class SubjectResponse(BaseModel):
    id: UUID
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CurriculumModuleResponse(BaseModel):
    id: UUID
    subject_id: UUID
    name: str
    description: Optional[str] = None
    order_index: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TopicResponse(BaseModel):
    id: UUID
    module_id: UUID
    name: str
    description: Optional[str] = None
    order_index: int
    created_at: datetime
    updated_at: datetime
    subject_id: Optional[UUID] = None
    subject_name: Optional[str] = None
    module_name: Optional[str] = None

    model_config = {"from_attributes": True}


class TopicTreeResponse(TopicResponse):
    pass


class ModuleTreeResponse(CurriculumModuleResponse):
    topics: List[TopicTreeResponse] = []


class SubjectTreeResponse(SubjectResponse):
    modules: List[ModuleTreeResponse] = []


class CurriculumTreePayload(BaseModel):
    subjects: List[SubjectTreeResponse]


class LegacyGroupMappingResponse(BaseModel):
    group_id: UUID
    group_name: str
    legacy_subject: Optional[str] = None
    current_subject_id: Optional[UUID] = None
    current_subject_name: Optional[str] = None
    suggested_subject_id: Optional[UUID] = None
    suggested_subject_name: Optional[str] = None


class LegacyQuestionMappingResponse(BaseModel):
    question_id: UUID
    assessment_id: Optional[UUID] = None
    assessment_title: Optional[str] = None
    content_preview: str
    legacy_topic: Optional[str] = None
    subject_id: Optional[UUID] = None
    subject_name: Optional[str] = None
    current_topic_id: Optional[UUID] = None
    current_topic_name: Optional[str] = None
    suggested_topic_id: Optional[UUID] = None
    suggested_topic_name: Optional[str] = None


class CurriculumReviewQueuePayload(BaseModel):
    groups: List[LegacyGroupMappingResponse]
    questions: List[LegacyQuestionMappingResponse]


class GroupSubjectAssignmentRequest(BaseModel):
    subject_id: UUID


class QuestionTopicAssignmentRequest(BaseModel):
    topic_id: UUID
