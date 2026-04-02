"""add direct subject attachment to assessments

Revision ID: 9b2f7a1c4d55
Revises: 5f7b7d6e2a11
Create Date: 2026-03-31 11:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "9b2f7a1c4d55"
down_revision: Union[str, Sequence[str], None] = "5f7b7d6e2a11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "assessments",
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_assessments_subject_id", "assessments", ["subject_id"], unique=False)
    op.create_foreign_key(
        "fk_assessments_subject_id_subjects",
        "assessments",
        "subjects",
        ["subject_id"],
        ["id"],
    )

    op.execute(
        """
        UPDATE assessments AS a
        SET subject_id = g.subject_id
        FROM groups AS g
        WHERE a.group_id = g.id
          AND a.subject_id IS NULL
          AND g.subject_id IS NOT NULL
        """
    )

    op.execute(
        """
        UPDATE assessments AS a
        SET subject_id = inferred.subject_id
        FROM (
            SELECT
                q.assessment_id,
                MIN(m.subject_id::text)::uuid AS subject_id
            FROM questions AS q
            JOIN topics AS t ON t.id = q.topic_id
            JOIN curriculum_modules AS m ON m.id = t.module_id
            WHERE q.assessment_id IS NOT NULL
            GROUP BY q.assessment_id
            HAVING COUNT(DISTINCT m.subject_id) = 1
        ) AS inferred
        WHERE a.id = inferred.assessment_id
          AND a.subject_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_constraint("fk_assessments_subject_id_subjects", "assessments", type_="foreignkey")
    op.drop_index("ix_assessments_subject_id", table_name="assessments")
    op.drop_column("assessments", "subject_id")
