"""Temporary audio validation and cleanup for batch voice requests."""

import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

MAX_AUDIO_BYTES = 10 * 1024 * 1024
READ_CHUNK_BYTES = 64 * 1024

SUPPORTED_EXTENSIONS = {".aac", ".m4a", ".mp3", ".mp4", ".ogg", ".wav", ".webm"}
MIME_EXTENSIONS = {
    "audio/aac": ".aac",
    "audio/mp4": ".m4a",
    "audio/mpeg": ".mp3",
    "audio/ogg": ".ogg",
    "audio/wav": ".wav",
    "audio/webm": ".webm",
    "audio/x-m4a": ".m4a",
    "audio/x-wav": ".wav",
}


class AudioValidationError(ValueError):
    """Base error for invalid uploaded audio."""


class EmptyAudioError(AudioValidationError):
    """Raised when an upload contains no audio bytes."""


class UnsupportedAudioError(AudioValidationError):
    """Raised when an upload format is unsupported."""


class AudioTooLargeError(AudioValidationError):
    """Raised when an upload exceeds the configured limit."""


@dataclass(frozen=True, slots=True)
class TemporaryAudio:
    path: Path
    size_bytes: int
    content_type: str


@asynccontextmanager
async def temporary_audio(upload: UploadFile) -> AsyncIterator[TemporaryAudio]:
    """Validate an upload, write it temporarily, and always delete it."""
    temp_path: Path | None = None

    try:
        suffix = _resolve_suffix(upload)
        content_type = (upload.content_type or "application/octet-stream").lower()

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = Path(temp_file.name)
            size_bytes = 0

            while chunk := await upload.read(READ_CHUNK_BYTES):
                size_bytes += len(chunk)
                if size_bytes > MAX_AUDIO_BYTES:
                    raise AudioTooLargeError
                temp_file.write(chunk)

        if size_bytes == 0:
            raise EmptyAudioError

        yield TemporaryAudio(
            path=temp_path,
            size_bytes=size_bytes,
            content_type=content_type,
        )
    finally:
        await upload.close()
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def _resolve_suffix(upload: UploadFile) -> str:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix:
        if suffix not in SUPPORTED_EXTENSIONS:
            raise UnsupportedAudioError
        return suffix

    content_type = (upload.content_type or "").split(";", maxsplit=1)[0].lower()
    try:
        return MIME_EXTENSIONS[content_type]
    except KeyError:
        raise UnsupportedAudioError from None
