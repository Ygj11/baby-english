"""Profile-aware Photo English endpoints."""

import logging
from time import perf_counter
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from server.app.api.dependencies import get_client_id
from server.app.api.voice import get_media_store, get_tts_gateway
from server.app.persistence.database import SessionFactory
from server.app.photo.gateway import VisionConfigurationError, VisionError, VisionGateway, create_vision_gateway
from server.app.photo.image import CorruptImageError, EmptyImageError, ImagePixelLimitError, ImageTooLargeError, UnsupportedImageError, temporary_image
from server.app.photo.repository import SQLAlchemyPhotoLearningRepository
from server.app.photo.schemas import PhotoAnalysisResponse, PhotoListenResponse, analysis_response
from server.app.photo.service import PhotoLearningService
from server.app.student_profile.repository import SQLAlchemyStudentProfileRepository
from server.app.student_profile.service import StudentProfileService
from server.app.tutor.schemas import StudentProfile
from server.app.voice.media import TemporaryMediaStore
from server.app.voice.tts import TTSError, TTSGateway


router = APIRouter(prefix="/api/photo", tags=["photo"])
logger = logging.getLogger("uvicorn.error.baby_english.photo")


async def require_photo_profile(
    client_id: Annotated[str, Depends(get_client_id)],
) -> StudentProfile:
    # Close the profile read session before any potentially slow provider call.
    async with SessionFactory() as session:
        profile = await StudentProfileService(
            SQLAlchemyStudentProfileRepository(session)
        ).get(client_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student profile setup is required.",
        )
    return profile


def get_vision_gateway() -> VisionGateway:
    try:
        return create_vision_gateway()
    except VisionConfigurationError as error:
        _log_failure("configuration", error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Photo English is temporarily unavailable.",
        ) from None


@router.post("/analyze", response_model=PhotoAnalysisResponse)
async def analyze_photo(
    file: Annotated[UploadFile, File()],
    client_id: Annotated[str, Depends(get_client_id)],
    student: Annotated[StudentProfile, Depends(require_photo_profile)],
    gateway: Annotated[VisionGateway, Depends(get_vision_gateway)],
) -> PhotoAnalysisResponse:
    started = perf_counter()
    try:
        async with temporary_image(file) as image:
            result = await PhotoLearningService(gateway).analyze(
                image_path=image.path,
                student=student,
            )
            record_id = None
            if result.status == "ok":
                async with SessionFactory() as session:
                    saved = await SQLAlchemyPhotoLearningRepository(session).save(
                        client_id, result
                    )
                    record_id = saved.id
    except EmptyImageError:
        raise HTTPException(status_code=400, detail="The image file is empty.") from None
    except (UnsupportedImageError, CorruptImageError):
        raise HTTPException(status_code=400, detail="The image format is unsupported.") from None
    except ImageTooLargeError:
        raise HTTPException(status_code=413, detail="The image file is too large.") from None
    except ImagePixelLimitError:
        raise HTTPException(status_code=413, detail="The image dimensions are too large.") from None
    except VisionError as error:
        _log_failure("request", error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Photo English is temporarily unavailable.",
        ) from None

    logger.info("photo_analysis_latency vision_ms=%d", round((perf_counter() - started) * 1000))
    return analysis_response(result, record_id)


@router.post("/records/{record_id}/listen", response_model=PhotoListenResponse)
async def listen_to_photo_phrase(
    record_id: int,
    client_id: Annotated[str, Depends(get_client_id)],
    _student: Annotated[StudentProfile, Depends(require_photo_profile)],
    tts: Annotated[TTSGateway, Depends(get_tts_gateway)],
    store: Annotated[TemporaryMediaStore, Depends(get_media_store)],
) -> PhotoListenResponse:
    async with SessionFactory() as session:
        record = await SQLAlchemyPhotoLearningRepository(session).get_owned(
            record_id, client_id
        )
    if record is None:
        raise HTTPException(status_code=404, detail="Photo learning record not found.")

    try:
        synthesized = await tts.synthesize(record.result.practice_phrase or "")
        media_id = store.save(synthesized)
    except TTSError as error:
        _log_failure("tts", error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Photo pronunciation is temporarily unavailable.",
        ) from None
    return PhotoListenResponse(audio_url=f"/api/voice/media/{media_id}")


def _log_failure(category: str, error: Exception) -> None:
    logger.warning(
        "provider_failure stage=photo category=%s exception=%s",
        category,
        type(error).__name__,
    )
