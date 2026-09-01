"""Create safe Photo English learning records.

Revision ID: 20260831_0004
Revises: 20260831_0003
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260831_0004"
down_revision: str | None = "20260831_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "photo_learning_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column("primary_word_en", sa.String(length=48), nullable=False),
        sa.Column("primary_meaning_zh", sa.String(length=48), nullable=False),
        sa.Column("simple_sentence_en", sa.String(length=180), nullable=False),
        sa.Column("simple_sentence_zh", sa.String(length=120), nullable=False),
        sa.Column("practice_phrase", sa.String(length=80), nullable=False),
        sa.Column("related_words_json", sa.Text(), nullable=False),
        sa.Column("question_en", sa.String(length=180), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sqlite_autoincrement=True,
    )
    op.create_index(
        "ix_photo_learning_records_client_id",
        "photo_learning_records",
        ["client_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_photo_learning_records_client_id", table_name="photo_learning_records")
    op.drop_table("photo_learning_records")
