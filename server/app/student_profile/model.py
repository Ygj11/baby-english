"""SQLAlchemy model for persisted student profiles."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from server.app.persistence.database import Base


class StudentProfileRecord(Base):
    __tablename__ = "student_profiles"
    __table_args__ = (
        CheckConstraint("age >= 6 AND age <= 12", name="ck_student_profiles_age"),
        CheckConstraint("grade >= 1 AND grade <= 6", name="ck_student_profiles_grade"),
        CheckConstraint(
            "english_level IN ('starter', 'beginner', 'elementary')",
            name="ck_student_profiles_english_level",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    grade: Mapped[int] = mapped_column(Integer, nullable=False)
    english_level: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
