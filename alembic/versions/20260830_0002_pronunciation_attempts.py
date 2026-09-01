"""Create pronunciation_attempts.

Revision ID: 20260830_0002
Revises: 20260830_0001
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260830_0002"
down_revision: str | None = "20260830_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pronunciation_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column("reference_text", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=16), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("accuracy_score", sa.Float(), nullable=False),
        sa.Column("fluency_score", sa.Float(), nullable=False),
        sa.Column("completeness_score", sa.Float(), nullable=True),
        sa.Column("standard_score", sa.Float(), nullable=True),
        sa.Column("rejected", sa.Boolean(), nullable=False),
        sa.Column("detail_json", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "category IN ('read_word', 'read_sentence')",
            name="ck_pronunciation_attempts_category",
        ),
        sa.CheckConstraint(
            "overall_score >= 0 AND overall_score <= 100",
            name="ck_pronunciation_attempts_overall_score",
        ),
        sa.CheckConstraint(
            "accuracy_score >= 0 AND accuracy_score <= 100",
            name="ck_pronunciation_attempts_accuracy_score",
        ),
        sa.CheckConstraint(
            "fluency_score >= 0 AND fluency_score <= 100",
            name="ck_pronunciation_attempts_fluency_score",
        ),
        sa.CheckConstraint(
            "completeness_score IS NULL OR (completeness_score >= 0 AND completeness_score <= 100)",
            name="ck_pronunciation_attempts_completeness_score",
        ),
        sa.CheckConstraint(
            "standard_score IS NULL OR (standard_score >= 0 AND standard_score <= 100)",
            name="ck_pronunciation_attempts_standard_score",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pronunciation_attempts_client_id",
        "pronunciation_attempts",
        ["client_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pronunciation_attempts_client_id",
        table_name="pronunciation_attempts",
    )
    op.drop_table("pronunciation_attempts")
