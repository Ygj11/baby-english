"""Batch voice HTTP endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from server.app.api.tutor import get_tutor_service
from server.app.tutor.llm import LLMError
from server.app.tutor.schemas import EnglishLevel, StudentProfile
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


class TranscriptionResponse(BaseModel):
    text: str
    duration_ms: int


class VoiceTurnResponse(BaseModel):
    transcript: str
    reply: str
    audio_url: str
    suggested_actions: list[str]


media_store = TemporaryMediaStore()


def get_stt_gateway() -> STTGateway:
    try:
        return create_stt()
    except STTConfigurationError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Speech recognition is temporarily unavailable.",
        ) from None


def get_tts_gateway() -> TTSGateway:
    try:
        return create_tts()
    except TTSConfigurationError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice tutor is temporarily unavailable.",
        ) from None


def get_media_store() -> TemporaryMediaStore:
    return media_store


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe(
    file: Annotated[UploadFile, File()],
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
    except STTError:
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
    age: Annotated[int, Form(ge=5, le=15)],
    grade: Annotated[int, Form(ge=1, le=9)],
    english_level: Annotated[EnglishLevel, Form()],
    stt: Annotated[STTGateway, Depends(get_stt_gateway)],
    tutor: Annotated[TutorService, Depends(get_tutor_service)],
    tts: Annotated[TTSGateway, Depends(get_tts_gateway)],
    store: Annotated[TemporaryMediaStore, Depends(get_media_store)],
) -> VoiceTurnResponse:
    try:
        async with temporary_audio(file) as audio:
            transcription = await stt.transcribe(audio.path)
            student = StudentProfile(
                age=age,
                grade=grade,
                english_level=english_level,
            )
            reply = await tutor.reply(transcription.text, student)
            synthesized = await tts.synthesize(reply)
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
    except (STTError, LLMError, TTSError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice tutor is temporarily unavailable.",
        ) from None

    return VoiceTurnResponse(
        transcript=transcription.text,
        reply=reply,
        audio_url=f"/api/voice/media/{media_id}",
        suggested_actions=["listen", "repeat", "explain_zh"],
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
