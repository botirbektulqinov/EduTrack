"""add hot path indexes

Revision ID: c4a8d21f6b90
Revises: 9b2f7a1c4d55
Create Date: 2026-04-29 18:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "c4a8d21f6b90"
down_revision: Union[str, Sequence[str], None] = "9b2f7a1c4d55"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_groups_teacher_archived", "groups", ["teacher_id", "is_archived"], unique=False)
    op.create_index("ix_group_enrollments_student_id", "group_enrollments", ["student_id"], unique=False)
    op.create_index("ix_assessments_teacher_created", "assessments", ["teacher_id", "created_at"], unique=False)
    op.create_index("ix_assessments_group_active_window", "assessments", ["group_id", "is_published", "is_active", "available_until"], unique=False)
    op.create_index("ix_questions_assessment_order", "questions", ["assessment_id", "order_index"], unique=False)
    op.create_index("ix_question_options_question_id", "question_options", ["question_id"], unique=False)
    op.create_index("ix_attempts_student_assessment", "assessment_attempts", ["student_id", "assessment_id"], unique=False)
    op.create_index("ix_attempts_assessment_status", "assessment_attempts", ["assessment_id", "status"], unique=False)
    op.create_index("ix_attempts_server_token", "assessment_attempts", ["server_token"], unique=False)
    op.create_index("ix_student_answers_attempt_question", "student_answers", ["attempt_id", "question_id"], unique=False)
    op.create_index("ix_student_answers_question_id", "student_answers", ["question_id"], unique=False)
    op.create_index("ix_violations_attempt_id", "violations", ["attempt_id"], unique=False)
    op.create_index("ix_violations_assessment_id", "violations", ["assessment_id"], unique=False)
    op.create_index("ix_violations_student_id", "violations", ["student_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_violations_student_id", table_name="violations")
    op.drop_index("ix_violations_assessment_id", table_name="violations")
    op.drop_index("ix_violations_attempt_id", table_name="violations")
    op.drop_index("ix_student_answers_question_id", table_name="student_answers")
    op.drop_index("ix_student_answers_attempt_question", table_name="student_answers")
    op.drop_index("ix_attempts_server_token", table_name="assessment_attempts")
    op.drop_index("ix_attempts_assessment_status", table_name="assessment_attempts")
    op.drop_index("ix_attempts_student_assessment", table_name="assessment_attempts")
    op.drop_index("ix_question_options_question_id", table_name="question_options")
    op.drop_index("ix_questions_assessment_order", table_name="questions")
    op.drop_index("ix_assessments_group_active_window", table_name="assessments")
    op.drop_index("ix_assessments_teacher_created", table_name="assessments")
    op.drop_index("ix_group_enrollments_student_id", table_name="group_enrollments")
    op.drop_index("ix_groups_teacher_archived", table_name="groups")
