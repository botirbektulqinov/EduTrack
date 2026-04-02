"""add question revisions

Revision ID: 3c1c7a9b0e12
Revises: 2b8f0f9a6d4f
Create Date: 2026-03-30 15:10:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "3c1c7a9b0e12"
down_revision = "2b8f0f9a6d4f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "question_revisions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("question_id", sa.UUID(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("summary", sa.String(length=255), nullable=True),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_question_revisions_created_by_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
            name=op.f("fk_question_revisions_question_id_questions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_question_revisions")),
        sa.UniqueConstraint("question_id", "version_number", name="uq_question_revision_version"),
    )


def downgrade() -> None:
    op.drop_table("question_revisions")
