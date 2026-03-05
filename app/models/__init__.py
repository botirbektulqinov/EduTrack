# app/models/__init__.py
"""
EduTrack — ORM Models Package
Import all models here so Alembic can detect them.
"""

from app.models.user import User
from app.models.department import Department
from app.models.group import Group
from app.models.group_enrollment import GroupEnrollment
from app.models.assessment import Assessment
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.question_bank import QuestionBank
from app.models.assessment_attempt import AssessmentAttempt
from app.models.student_answer import StudentAnswer
from app.models.violation import Violation
from app.models.performance_snapshot import PerformanceSnapshot
from app.models.audit_log import AuditLog
from app.models.notification import Notification

__all__ = [
    "User",
    "Department",
    "Group",
    "GroupEnrollment",
    "Assessment",
    "Question",
    "QuestionOption",
    "QuestionBank",
    "AssessmentAttempt",
    "StudentAnswer",
    "Violation",
    "PerformanceSnapshot",
    "AuditLog",
    "Notification",
]
