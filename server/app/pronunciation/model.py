"""SQLAlchemy model for normalized pronunciation attempts."""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from server.app.persistence.database import Base


class PronunciationAttemptRecord(Base):
    __tablename__ = "pronunciation_attempts"
    __table_args__ = (
        CheckConstraint(
            "category IN ('read_word', 'read_sentence')",
            name="ck_pronunciation_attempts_category",
        ),
        CheckConstraint(
            "overall_score >= 0 AND overall_score <= 100",
            name="ck_pronunciation_attempts_overall_score",
        ),
        CheckConstraint(
            "accuracy_score >= 0 AND accuracy_score <= 100",
            name="ck_pronunciation_attempts_accuracy_score",
        ),
        CheckConstraint(
            "fluency_score >= 0 AND fluency_score <= 100",
            name="ck_pronunciation_attempts_fluency_score",
        ),
        CheckConstraint(
            "completeness_score IS NULL OR (completeness_score >= 0 AND completeness_score <= 100)",
            name="ck_pronunciation_attempts_completeness_score",
        ),
        CheckConstraint(
            "standard_score IS NULL OR (standard_score >= 0 AND standard_score <= 100)",
            name="ck_pronunciation_attempts_standard_score",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reference_text: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    accuracy_score: Mapped[float] = mapped_column(Float, nullable=False)
    fluency_score: Mapped[float] = mapped_column(Float, nullable=False)
    completeness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    standard_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rejected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    detail_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )
