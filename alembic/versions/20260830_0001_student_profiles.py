"""Create student_profiles.

Revision ID: 20260830_0001
Revises:
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260830_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "student_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=False),
        sa.Column("english_level", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("age >= 6 AND age <= 12", name="ck_student_profiles_age"),
        sa.CheckConstraint("grade >= 1 AND grade <= 6", name="ck_student_profiles_grade"),
        sa.CheckConstraint(
            "english_level IN ('starter', 'beginner', 'elementary')",
            name="ck_student_profiles_english_level",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_student_profiles_client_id",
        "student_profiles",
        ["client_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_student_profiles_client_id", table_name="student_profiles")
    op.drop_table("student_profiles")
