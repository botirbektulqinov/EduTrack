"""add curriculum structure

Revision ID: 2b8f0f9a6d4f
Revises: 083bc3634e98
Create Date: 2026-03-30 13:10:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2b8f0f9a6d4f"
down_revision = "083bc3634e98"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subjects",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_subjects")),
        sa.UniqueConstraint("name", name=op.f("uq_subjects_name")),
    )

    op.create_table(
        "curriculum_modules",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("subject_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["subject_id"],
            ["subjects.id"],
            name=op.f("fk_curriculum_modules_subject_id_subjects"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_curriculum_modules")),
        sa.UniqueConstraint("subject_id", "name", name="uq_curriculum_module_subject_name"),
    )

    op.create_table(
        "topics",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("module_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["module_id"],
            ["curriculum_modules.id"],
            name=op.f("fk_topics_module_id_curriculum_modules"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_topics")),
        sa.UniqueConstraint("module_id", "name", name="uq_topic_module_name"),
    )

    op.add_column("groups", sa.Column("subject_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        op.f("fk_groups_subject_id_subjects"),
        "groups",
        "subjects",
        ["subject_id"],
        ["id"],
    )

    op.add_column("questions", sa.Column("topic_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        op.f("fk_questions_topic_id_topics"),
        "questions",
        "topics",
        ["topic_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_questions_topic_id_topics"), "questions", type_="foreignkey")
    op.drop_column("questions", "topic_id")

    op.drop_constraint(op.f("fk_groups_subject_id_subjects"), "groups", type_="foreignkey")
    op.drop_column("groups", "subject_id")

    op.drop_table("topics")
    op.drop_table("curriculum_modules")
    op.drop_table("subjects")
