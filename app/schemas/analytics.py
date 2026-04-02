"""
EduTrack — Analytics Schemas
Dashboard data structures.
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Student Dashboard ──

class StudentDashboardResponse(BaseModel):
    student_name: Optional[str] = None
    selected_semester: Optional[str] = None
    available_semesters: List[str] = Field(default_factory=list)
    overall_score_avg: Optional[float]
    pass_rate: Optional[float]
    assessments_taken: int
    assessments_passed: int
    streak_count: int
    improvement_rate: Optional[float]
    violation_count_total: int
    score_trend: List[Dict]  # [{date, score, assessment_title}]
    subject_scores: List[Dict]  # [{subject, avg_score}]
    weak_topics: List[str]
    topic_performance: List[Dict] = Field(default_factory=list)
    comparison_summary: Optional[Dict] = None
    insights: List[str] = Field(default_factory=list)
    recent_results: List[Dict]


class SubjectBreakdownResponse(BaseModel):
    subject: str
    assessments_taken: int
    avg_score: Optional[float]
    best_score: Optional[float]
    pass_rate: Optional[float]


# ── Teacher Dashboard ──

class ClassPerformanceResponse(BaseModel):
    group_id: UUID
    group_name: str
    student_count: int
    avg_score: Optional[float]
    pass_rate: Optional[float]
    score_distribution: List[Dict]  # [{range, count}]
    at_risk_students: List[Dict]  # [{student_id, full_name, avg_score}]


class AssessmentStatsResponse(BaseModel):
    assessment_id: UUID
    title: str
    attempts_count: int
    mean_score: Optional[float]
    median_score: Optional[float]
    std_deviation: Optional[float]
    pass_rate: Optional[float]
    min_score: Optional[float]
    max_score: Optional[float]


class ItemAnalysisResponse(BaseModel):
    question_id: UUID
    question_type: str
    content: str
    difficulty_index: Optional[float]  # p = correct / total
    discrimination_index: Optional[float]  # D = p_upper - p_lower
    point_biserial: Optional[float]
    distractor_analysis: Optional[Dict]  # {option_id: percent_chosen}
    classification: str  # easy, medium, hard, flawed


# ── Admin Dashboard ──

class AdminOverviewResponse(BaseModel):
    total_students: int
    total_teachers: int
    total_groups: int
    total_assessments: int
    university_pass_rate: Optional[float]
    department_stats: List[Dict]  # [{department, avg_score, pass_rate}]
    violation_summary: Dict  # {type: count}
    completion_rate: Optional[float]
    semester_trends: List[Dict]  # [{semester, avg_score, pass_rate}]
