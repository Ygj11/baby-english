"""Batch voice HTTP endpoints."""

import logging
from time import perf_counter
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from server.app.api.dependencies import get_client_id, require_student_profile
from server.app.api.tutor import get_tutor_service
from server.app.tutor.llm import LLMError
from server.app.tutor.repeat_target import extract_repeat_target
from server.app.tutor.schemas import StudentProfile
from server.app.tutor.service import TutorService
from server.app.voice.audio import (
    AudioTooLargeError,
    EmptyAudioError,
    UnsupportedAudioError,
    temporary_audio,
)
from server.app.voice.stt import (
    STTConfigurationError,
    STTError,
    STTGateway,
    create_stt,
)
from server.app.voice.media import TemporaryMediaStore
from server.app.voice.tts import (
    TTSConfigurationError,
    TTSError,
    TTSGateway,
    create_tts,
)

router = APIRouter(prefix="/api/voice", tags=["voice"])
logger = logging.getLogger("uvicorn.error.baby_english.voice")


class TranscriptionResponse(BaseModel):
    text: str
    duration_ms: int


class VoiceTurnResponse(BaseModel):
    transcript: str
    reply: str
    repeat_text: str | None
    audio_url: str
    suggested_actions: list[str]


media_store = TemporaryMediaStore()


def get_stt_gateway() -> STTGateway:
    try:
        return create_stt()
    except STTConfigurationError as error:
        _log_provider_failure("stt", "configuration", error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Speech recognition is temporarily unavailable.",
        ) from None


def get_tts_gateway() -> TTSGateway:
    try:
        return create_tts()
    except TTSConfigurationError as error:
        _log_provider_failure("tts", "configuration", error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice tutor is temporarily unavailable.",
        ) from None


def get_media_store() -> TemporaryMediaStore:
    return media_store


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe(
    file: Annotated[UploadFile, File()],
    _client_id: Annotated[str, Depends(get_client_id)],
    gateway: Annotated[STTGateway, Depends(get_stt_gateway)],
) -> TranscriptionResponse:
    try:
        async with temporary_audio(file) as audio:
            result = await gateway.transcribe(audio.path)
    except EmptyAudioError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The audio file is empty.",
        ) from None
    except UnsupportedAudioError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The audio format is unsupported.",
        ) from None
    except AudioTooLargeError:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="The audio file is too large.",
        ) from None
    except STTError as error:
        _log_provider_failure("stt", "request", error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Speech recognition is temporarily unavailable.",
        ) from None

    return TranscriptionResponse(
        text=result.text,
        duration_ms=result.duration_ms,
    )


@router.post("/turn", response_model=VoiceTurnResponse)
async def voice_turn(
    file: Annotated[UploadFile, File()],
    student: Annotated[StudentProfile, Depends(require_student_profile)],
    stt: Annotated[STTGateway, Depends(get_stt_gateway)],
    tutor: Annotated[TutorService, Depends(get_tutor_service)],
    tts: Annotated[TTSGateway, Depends(get_tts_gateway)],
    store: Annotated[TemporaryMediaStore, Depends(get_media_store)],
) -> VoiceTurnResponse:
    total_started = perf_counter()
    stage = "stt"
    try:
        async with temporary_audio(file) as audio:
            stage_started = perf_counter()
            transcription = await stt.transcribe(audio.path)
            stt_ms = _elapsed_ms(stage_started)

            stage = "llm"
            stage_started = perf_counter()
            reply = await tutor.reply(transcription.text, student)
            llm_ms = _elapsed_ms(stage_started)

            stage = "tts"
            stage_started = perf_counter()
            synthesized = await tts.synthesize(reply)
            tts_ms = _elapsed_ms(stage_started)
            media_id = store.save(synthesized)
    except EmptyAudioError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The audio file is empty.",
        ) from None
    except UnsupportedAudioError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The audio format is unsupported.",
        ) from None
    except AudioTooLargeError:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="The audio file is too large.",
        ) from None
    except (STTError, LLMError, TTSError) as error:
        _log_provider_failure(stage, "request", error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice tutor is temporarily unavailable.",
        ) from None

    total_ms = _elapsed_ms(total_started)
    logger.info(
        "voice_turn_latency stt_ms=%d llm_ms=%d tts_ms=%d total_ms=%d",
        stt_ms,
        llm_ms,
        tts_ms,
        total_ms,
    )

    repeat_text = extract_repeat_target(reply)
    actions = ["listen", "explain_zh"]
    if repeat_text is not None:
        actions.insert(1, "repeat")
    return VoiceTurnResponse(
        transcript=transcription.text,
        reply=reply,
        repeat_text=repeat_text,
        audio_url=f"/api/voice/media/{media_id}",
        suggested_actions=actions,
    )


@router.get("/media/{media_id}", response_class=FileResponse)
async def voice_media(
    media_id: str,
    store: Annotated[TemporaryMediaStore, Depends(get_media_store)],
) -> FileResponse:
    asset = store.get(media_id)
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio is unavailable.",
        )

    return FileResponse(
        path=asset.path,
        media_type=asset.content_type,
        headers={"Cache-Control": "private, max-age=300"},
    )


def _elapsed_ms(started: float) -> int:
    return round((perf_counter() - started) * 1000)


def _log_provider_failure(stage: str, category: str, error: Exception) -> None:
    logger.warning(
        "provider_failure stage=%s category=%s exception=%s",
        stage,
        category,
        type(error).__name__,
    )
