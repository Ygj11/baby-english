"""Create scenario session memory and goal progress.

Revision ID: 20260831_0003
Revises: 20260830_0002
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260831_0003"
down_revision: str | None = "20260830_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scenario_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column("scene_id", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("completed_goal_ids_json", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("tip", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('active', 'completed')", name="ck_scenario_sessions_status"),
        sa.PrimaryKeyConstraint("id"),
        sqlite_autoincrement=True,
    )
    op.create_index("ix_scenario_sessions_client_id", "scenario_sessions", ["client_id"], unique=False)
    op.create_index("ix_scenario_sessions_scene_id", "scenario_sessions", ["scene_id"], unique=False)

    op.create_table(
        "scenario_turns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("idx", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("idx >= 0", name="ck_scenario_turns_idx"),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="ck_scenario_turns_role"),
        sa.ForeignKeyConstraint(["session_id"], ["scenario_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "idx", name="uq_scenario_turns_session_idx"),
    )
    op.create_index("ix_scenario_turns_session_id", "scenario_turns", ["session_id"], unique=False)

    op.create_table(
        "scene_goal_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column("scene_id", sa.String(length=32), nullable=False),
        sa.Column("goal_id", sa.String(length=32), nullable=False),
        sa.Column("completion_count", sa.Integer(), nullable=False),
        sa.Column("first_completed_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("last_completed_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("completion_count >= 1", name="ck_scene_goal_progress_count"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id", "scene_id", "goal_id", name="uq_scene_goal_progress_owner_goal"),
    )
    op.create_index("ix_scene_goal_progress_client_id", "scene_goal_progress", ["client_id"], unique=False)
    op.create_index("ix_scene_goal_progress_scene_id", "scene_goal_progress", ["scene_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_scene_goal_progress_scene_id", table_name="scene_goal_progress")
    op.drop_index("ix_scene_goal_progress_client_id", table_name="scene_goal_progress")
    op.drop_table("scene_goal_progress")
    op.drop_index("ix_scenario_turns_session_id", table_name="scenario_turns")
    op.drop_table("scenario_turns")
    op.drop_index("ix_scenario_sessions_scene_id", table_name="scenario_sessions")
    op.drop_index("ix_scenario_sessions_client_id", table_name="scenario_sessions")
    op.drop_table("scenario_sessions")
