"""SQLAlchemy model for safe Photo English learning facts."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from server.app.persistence.database import Base


class PhotoLearningRecordModel(Base):
    __tablename__ = "photo_learning_records"
    __table_args__ = ({"sqlite_autoincrement": True},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    primary_word_en: Mapped[str] = mapped_column(String(48), nullable=False)
    primary_meaning_zh: Mapped[str] = mapped_column(String(48), nullable=False)
    simple_sentence_en: Mapped[str] = mapped_column(String(180), nullable=False)
    simple_sentence_zh: Mapped[str] = mapped_column(String(120), nullable=False)
    practice_phrase: Mapped[str] = mapped_column(String(80), nullable=False)
    related_words_json: Mapped[str] = mapped_column(Text, nullable=False)
    question_en: Mapped[str] = mapped_column(String(180), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )
