"""SQLAlchemy metadata models for indexed textbooks and student selection."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from server.app.persistence.database import Base


class TextbookRecord(Base):
    __tablename__ = "textbooks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    publisher: Mapped[str] = mapped_column(String(120), nullable=False)
    series: Mapped[str] = mapped_column(String(120), nullable=False)
    grade: Mapped[int] = mapped_column(Integer, nullable=False)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(120), nullable=False)
    embedding_dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    index_schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )


class TextbookUnitRecord(Base):
    __tablename__ = "textbook_units"
    __table_args__ = (UniqueConstraint("textbook_id", "unit_no", name="uq_textbook_units_book_unit"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    textbook_id: Mapped[int] = mapped_column(
        ForeignKey("textbooks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    unit_no: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )


class StudentTextbookRecord(Base):
    __tablename__ = "student_textbooks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    textbook_id: Mapped[int] = mapped_column(
        ForeignKey("textbooks.id", ondelete="CASCADE"), nullable=False
    )
    current_unit_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )
