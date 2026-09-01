"""Create textbook metadata and per-client selection.

Revision ID: 20260831_0005
Revises: 20260831_0004
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260831_0005"
down_revision: str | None = "20260831_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "textbooks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("publisher", sa.String(length=120), nullable=False),
        sa.Column("series", sa.String(length=120), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=False),
        sa.Column("semester", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("embedding_model", sa.String(length=120), nullable=False),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=False),
        sa.Column("index_schema_version", sa.Integer(), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_textbooks_slug", "textbooks", ["slug"], unique=True)
    op.create_table(
        "textbook_units",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("textbook_id", sa.Integer(), nullable=False),
        sa.Column("unit_no", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["textbook_id"], ["textbooks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("textbook_id", "unit_no", name="uq_textbook_units_book_unit"),
    )
    op.create_index("ix_textbook_units_textbook_id", "textbook_units", ["textbook_id"], unique=False)
    op.create_table(
        "student_textbooks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column("textbook_id", sa.Integer(), nullable=False),
        sa.Column("current_unit_no", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["textbook_id"], ["textbooks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_student_textbooks_client_id", "student_textbooks", ["client_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_student_textbooks_client_id", table_name="student_textbooks")
    op.drop_table("student_textbooks")
    op.drop_index("ix_textbook_units_textbook_id", table_name="textbook_units")
    op.drop_table("textbook_units")
    op.drop_index("ix_textbooks_slug", table_name="textbooks")
    op.drop_table("textbooks")
