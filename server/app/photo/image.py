"""Bounded temporary image validation and privacy-preserving normalization."""

from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
import tempfile
import warnings
from collections.abc import AsyncIterator

from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError


MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000
MAX_LONG_EDGE = 1600
CHUNK_SIZE = 256 * 1024
SUPPORTED_FORMATS = {"JPEG", "PNG", "WEBP"}
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
SUPPORTED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
EXPECTED_FORMATS = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".webp": "WEBP",
}
EXPECTED_CONTENT_TYPE_FORMATS = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}


class ImageInputError(ValueError):
    """Base class for rejected image uploads."""


class EmptyImageError(ImageInputError):
    pass


class UnsupportedImageError(ImageInputError):
    pass


class CorruptImageError(ImageInputError):
    pass


class ImageTooLargeError(ImageInputError):
    pass


class ImagePixelLimitError(ImageInputError):
    pass


@dataclass(frozen=True, slots=True)
class TemporaryImage:
    path: Path
    content_type: str
    width: int
    height: int
    byte_count: int


@asynccontextmanager
async def temporary_image(
    upload: UploadFile,
    *,
    base_dir: Path | None = None,
) -> AsyncIterator[TemporaryImage]:
    """Yield a normalized JPEG and always remove every temporary copy."""
    filename = upload.filename or ""
    suffix = Path(filename).suffix.lower()
    content_type = (upload.content_type or "").lower()
    if suffix not in SUPPORTED_EXTENSIONS or content_type not in SUPPORTED_CONTENT_TYPES:
        raise UnsupportedImageError
    if EXPECTED_FORMATS[suffix] != EXPECTED_CONTENT_TYPE_FORMATS[content_type]:
        raise UnsupportedImageError

    original_path: Path | None = None
    normalized_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix="baby-english-photo-original-",
            suffix=suffix,
            dir=base_dir,
            delete=False,
        ) as original:
            original_path = Path(original.name)
            byte_count = 0
            while chunk := await upload.read(CHUNK_SIZE):
                byte_count += len(chunk)
                if byte_count > MAX_IMAGE_BYTES:
                    raise ImageTooLargeError
                original.write(chunk)
        if byte_count == 0:
            raise EmptyImageError

        with tempfile.NamedTemporaryFile(
            prefix="baby-english-photo-normalized-",
            suffix=".jpg",
            dir=base_dir,
            delete=False,
        ) as normalized:
            normalized_path = Path(normalized.name)

        width, height = _normalize(
            original_path,
            normalized_path,
            expected_format=EXPECTED_FORMATS[suffix],
        )
        yield TemporaryImage(
            path=normalized_path,
            content_type="image/jpeg",
            width=width,
            height=height,
            byte_count=normalized_path.stat().st_size,
        )
    finally:
        await upload.close()
        if original_path is not None:
            original_path.unlink(missing_ok=True)
        if normalized_path is not None:
            normalized_path.unlink(missing_ok=True)


def _normalize(source: Path, target: Path, *, expected_format: str) -> tuple[int, int]:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(source) as probe:
                if probe.format not in SUPPORTED_FORMATS or probe.format != expected_format:
                    raise UnsupportedImageError
                if getattr(probe, "is_animated", False) or getattr(probe, "n_frames", 1) != 1:
                    raise UnsupportedImageError
                if probe.width <= 0 or probe.height <= 0:
                    raise CorruptImageError
                if probe.width * probe.height > MAX_IMAGE_PIXELS:
                    raise ImagePixelLimitError
                probe.verify()

            with Image.open(source) as opened:
                opened.load()
                oriented = ImageOps.exif_transpose(opened)
                if oriented.mode in {"RGBA", "LA"}:
                    background = Image.new("RGB", oriented.size, "white")
                    alpha = oriented.getchannel("A")
                    background.paste(oriented.convert("RGB"), mask=alpha)
                    rgb = background
                else:
                    rgb = oriented.convert("RGB")
                rgb.thumbnail((MAX_LONG_EDGE, MAX_LONG_EDGE), Image.Resampling.LANCZOS)
                rgb.save(target, format="JPEG", quality=88, optimize=True)
                return rgb.size
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise ImagePixelLimitError from error
    except (UnidentifiedImageError, OSError, SyntaxError) as error:
        raise CorruptImageError from error
