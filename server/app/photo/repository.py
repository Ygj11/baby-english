"""Minimal persistence boundary for safe Photo English learning records."""

from dataclasses import dataclass
import json
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.photo.domain import PhotoLearningResult, RelatedWord
from server.app.photo.model import PhotoLearningRecordModel


@dataclass(frozen=True, slots=True)
class StoredPhotoLearningRecord:
    id: int
    client_id: str
    result: PhotoLearningResult


class PhotoLearningRepository(Protocol):
    async def save(self, client_id: str, result: PhotoLearningResult) -> StoredPhotoLearningRecord: ...
    async def get_owned(self, record_id: int, client_id: str) -> StoredPhotoLearningRecord | None: ...


class SQLAlchemyPhotoLearningRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, client_id: str, result: PhotoLearningResult) -> StoredPhotoLearningRecord:
        if result.status != "ok":
            raise ValueError("Only successful Photo English lessons may be persisted.")
        record = PhotoLearningRecordModel(
            client_id=client_id,
            primary_word_en=result.primary_word_en,
            primary_meaning_zh=result.primary_meaning_zh,
            simple_sentence_en=result.simple_sentence_en,
            simple_sentence_zh=result.simple_sentence_zh,
            practice_phrase=result.practice_phrase,
            related_words_json=json.dumps(
                [
                    {"word_en": item.word_en, "meaning_zh": item.meaning_zh}
                    for item in result.related_words
                ],
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            question_en=result.question_en,
        )
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return _to_domain(record)

    async def get_owned(self, record_id: int, client_id: str) -> StoredPhotoLearningRecord | None:
        row = await self._session.execute(
            select(PhotoLearningRecordModel).where(
                PhotoLearningRecordModel.id == record_id,
                PhotoLearningRecordModel.client_id == client_id,
            )
        )
        record = row.scalar_one_or_none()
        return _to_domain(record) if record is not None else None


def _to_domain(record: PhotoLearningRecordModel) -> StoredPhotoLearningRecord:
    related = json.loads(record.related_words_json)
    return StoredPhotoLearningRecord(
        id=record.id,
        client_id=record.client_id,
        result=PhotoLearningResult(
            status="ok",
            primary_word_en=record.primary_word_en,
            primary_meaning_zh=record.primary_meaning_zh,
            simple_sentence_en=record.simple_sentence_en,
            simple_sentence_zh=record.simple_sentence_zh,
            practice_phrase=record.practice_phrase,
            related_words=tuple(RelatedWord(**item) for item in related),
            question_en=record.question_en,
            encouragement_zh="很好！继续读一读吧。",
        ),
    )
