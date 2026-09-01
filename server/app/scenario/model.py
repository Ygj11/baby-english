"""SQLAlchemy records for active scenario memory and durable goal progress."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from server.app.persistence.database import Base


class ScenarioSessionRecord(Base):
    __tablename__ = "scenario_sessions"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'completed')", name="ck_scenario_sessions_status"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    scene_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    completed_goal_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tip: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.current_timestamp())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ScenarioTurnRecord(Base):
    __tablename__ = "scenario_turns"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="ck_scenario_turns_role"),
        CheckConstraint("idx >= 0", name="ck_scenario_turns_idx"),
        UniqueConstraint("session_id", "idx", name="uq_scenario_turns_session_idx"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("scenario_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    idx: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.current_timestamp())


class SceneGoalProgressRecord(Base):
    __tablename__ = "scene_goal_progress"
    __table_args__ = (
        CheckConstraint("completion_count >= 1", name="ck_scene_goal_progress_count"),
        UniqueConstraint("client_id", "scene_id", "goal_id", name="uq_scene_goal_progress_owner_goal"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    scene_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    goal_id: Mapped[str] = mapped_column(String(32), nullable=False)
    completion_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    first_completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.current_timestamp())
    last_completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.current_timestamp())
