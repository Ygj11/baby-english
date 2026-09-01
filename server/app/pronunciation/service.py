"""Pronunciation evaluation application service."""

from dataclasses import dataclass
from pathlib import Path

from server.app.pronunciation.domain import PronunciationResult
from server.app.pronunciation.feedback import child_feedback
from server.app.pronunciation.gateway import PronunciationGateway
from server.app.pronunciation.reference import choose_category, normalize_reference_text
from server.app.pronunciation.repository import PronunciationAttemptRepository


@dataclass(frozen=True, slots=True)
class PronunciationEvaluation:
    attempt_id: int
    reference_text: str
    result: PronunciationResult
    feedback: str


@dataclass(slots=True)
class PronunciationPracticeService:
    gateway: PronunciationGateway
    repository: PronunciationAttemptRepository

    async def evaluate(
        self,
        *,
        client_id: str,
        reference_text: str,
        audio_path: Path,
    ) -> PronunciationEvaluation:
        reference = normalize_reference_text(reference_text)
        category = choose_category(reference)
        result = await self.gateway.evaluate(
            reference_text=reference,
            audio_path=audio_path,
            category=category,
        )
        attempt_id = await self.repository.save(
            client_id=client_id,
            reference_text=reference,
            category=category,
            result=result,
        )
        return PronunciationEvaluation(
            attempt_id=attempt_id,
            reference_text=reference,
            result=result,
            feedback=child_feedback(result),
        )
