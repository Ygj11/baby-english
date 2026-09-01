"""Pronunciation practice API."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.dependencies import get_client_id, require_student_profile
from server.app.persistence.database import get_session
from server.app.pronunciation.gateway import (
    PronunciationConfigurationError,
    PronunciationError,
    PronunciationGateway,
    create_pronunciation_gateway,
)
from server.app.pronunciation.reference import InvalidReferenceTextError
from server.app.pronunciation.repository import SQLAlchemyPronunciationAttemptRepository
from server.app.pronunciation.service import PronunciationPracticeService
from server.app.tutor.schemas import StudentProfile
from server.app.voice.audio import (
    AudioTooLargeError,
    EmptyAudioError,
    UnsupportedAudioError,
    temporary_audio,
)


router = APIRouter(prefix="/api/pronunciation", tags=["pronunciation"])
logger = logging.getLogger("uvicorn.error.baby_english.pronunciation")


class WordScoreResponse(BaseModel):
    word: str
    score: float | None


class PronunciationResponse(BaseModel):
    attempt_id: int
    reference_text: str
    overall_score: float
    accuracy_score: float
    fluency_score: float
    completeness_score: float | None
    standard_score: float | None
    rejected: bool
    words: list[WordScoreResponse]
    feedback: str


def get_pronunciation_gateway() -> PronunciationGateway:
    try:
        return create_pronunciation_gateway()
    except PronunciationConfigurationError as error:
        _log_provider_failure("configuration", error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pronunciation practice is temporarily unavailable.",
        ) from None


def get_pronunciation_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    gateway: Annotated[PronunciationGateway, Depends(get_pronunciation_gateway)],
) -> PronunciationPracticeService:
    return PronunciationPracticeService(
        gateway=gateway,
        repository=SQLAlchemyPronunciationAttemptRepository(session),
    )


@router.post("/evaluate", response_model=PronunciationResponse)
async def evaluate_pronunciation(
    file: Annotated[UploadFile, File()],
    client_id: Annotated[str, Depends(get_client_id)],
    _student: Annotated[StudentProfile, Depends(require_student_profile)],
    service: Annotated[PronunciationPracticeService, Depends(get_pronunciation_service)],
    reference_text: Annotated[str | None, Form()] = None,
) -> PronunciationResponse:
    try:
        async with temporary_audio(file) as audio:
            if audio.path.suffix.lower() != ".mp3":
                raise UnsupportedAudioError
            evaluation = await service.evaluate(
                client_id=client_id,
                reference_text=reference_text or "",
                audio_path=audio.path,
            )
    except InvalidReferenceTextError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The pronunciation target is invalid.",
        ) from None
    except EmptyAudioError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The audio file is empty.",
        ) from None
    except UnsupportedAudioError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pronunciation practice requires MP3 audio.",
        ) from None
    except AudioTooLargeError:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="The audio file is too large.",
        ) from None
    except PronunciationError as error:
        _log_provider_failure("request", error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pronunciation practice is temporarily unavailable.",
        ) from None

    result = evaluation.result
    return PronunciationResponse(
        attempt_id=evaluation.attempt_id,
        reference_text=evaluation.reference_text,
        overall_score=result.overall_score,
        accuracy_score=result.accuracy_score,
        fluency_score=result.fluency_score,
        completeness_score=result.completeness_score,
        standard_score=result.standard_score,
        rejected=result.rejected,
        words=[WordScoreResponse(word=word.word, score=word.score) for word in result.words],
        feedback=evaluation.feedback,
    )


def _log_provider_failure(category: str, error: Exception) -> None:
    logger.warning(
        "provider_failure stage=ise category=%s exception=%s",
        category,
        type(error).__name__,
    )
