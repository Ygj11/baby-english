"""Persistence boundary for normalized pronunciation attempts."""

import json
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from server.app.pronunciation.domain import EvaluationCategory, PronunciationResult
from server.app.pronunciation.model import PronunciationAttemptRecord


class PronunciationAttemptRepository(Protocol):
    async def save(
        self,
        *,
        client_id: str,
        reference_text: str,
        category: EvaluationCategory,
        result: PronunciationResult,
    ) -> int: ...


class SQLAlchemyPronunciationAttemptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(
        self,
        *,
        client_id: str,
        reference_text: str,
        category: EvaluationCategory,
        result: PronunciationResult,
    ) -> int:
        detail = [
            {
                "word": word.word,
                "score": word.score,
                "issues": [
                    {"kind": issue.kind, "unit": issue.unit}
                    for issue in word.issues
                ],
            }
            for word in result.words
        ]
        record = PronunciationAttemptRecord(
            client_id=client_id,
            reference_text=reference_text,
            category=category,
            overall_score=result.overall_score,
            accuracy_score=result.accuracy_score,
            fluency_score=result.fluency_score,
            completeness_score=result.completeness_score,
            standard_score=result.standard_score,
            rejected=result.rejected,
            detail_json=json.dumps(detail, ensure_ascii=True, separators=(",", ":")),
        )
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return record.id
