from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from starlette.datastructures import Headers, UploadFile

import server.app.photo.image as image_module
from server.app.photo.image import (
    CorruptImageError,
    EmptyImageError,
    ImagePixelLimitError,
    ImageTooLargeError,
    MAX_LONG_EDGE,
    UnsupportedImageError,
    temporary_image,
)


def image_bytes(
    image_format: str,
    *,
    size: tuple[int, int] = (40, 20),
    exif: Image.Exif | None = None,
) -> bytes:
    output = BytesIO()
    options = {"exif": exif} if exif is not None else {}
    Image.new("RGB", size, "red").save(output, format=image_format, **options)
    return output.getvalue()


def upload(data: bytes, filename: str, content_type: str) -> UploadFile:
    return UploadFile(
        BytesIO(data),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("image_format", "filename", "content_type"),
    [
        ("JPEG", "photo.jpg", "image/jpeg"),
        ("PNG", "photo.png", "image/png"),
        ("WEBP", "photo.webp", "image/webp"),
    ],
)
async def test_supported_images_are_normalized_to_metadata_free_jpeg_and_cleaned(
    tmp_path: Path,
    image_format: str,
    filename: str,
    content_type: str,
) -> None:
    yielded_path = None
    async with temporary_image(
        upload(image_bytes(image_format), filename, content_type), base_dir=tmp_path
    ) as normalized:
        yielded_path = normalized.path
        assert normalized.content_type == "image/jpeg"
        assert normalized.path.exists()
        with Image.open(normalized.path) as opened:
            assert opened.format == "JPEG"
            assert opened.getexif() == {}
    assert yielded_path is not None and not yielded_path.exists()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_exif_orientation_is_applied_and_exif_is_removed(tmp_path: Path) -> None:
    exif = Image.Exif()
    exif[274] = 6
    exif[315] = "private camera owner"
    async with temporary_image(
        upload(image_bytes("JPEG", exif=exif), "oriented.jpg", "image/jpeg"),
        base_dir=tmp_path,
    ) as normalized:
        assert (normalized.width, normalized.height) == (20, 40)
        with Image.open(normalized.path) as opened:
            assert opened.getexif() == {}
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_large_image_is_resized_within_long_edge(tmp_path: Path) -> None:
    async with temporary_image(
        upload(image_bytes("JPEG", size=(2000, 1000)), "large.jpg", "image/jpeg"),
        base_dir=tmp_path,
    ) as normalized:
        assert max(normalized.width, normalized.height) == MAX_LONG_EDGE
        assert (normalized.width, normalized.height) == (1600, 800)


@pytest.mark.asyncio
async def test_animated_webp_is_rejected_and_cleaned(tmp_path: Path) -> None:
    output = BytesIO()
    frames = [Image.new("RGB", (8, 8), color) for color in ("red", "blue")]
    frames[0].save(
        output,
        format="WEBP",
        save_all=True,
        append_images=frames[1:],
        duration=100,
        loop=0,
    )
    with pytest.raises(UnsupportedImageError):
        async with temporary_image(
            upload(output.getvalue(), "animated.webp", "image/webp"),
            base_dir=tmp_path,
        ):
            pass
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("data", "filename", "content_type", "expected"),
    [
        (b"", "empty.jpg", "image/jpeg", EmptyImageError),
        (b"not an image", "broken.jpg", "image/jpeg", CorruptImageError),
        (b"GIF89a", "photo.gif", "image/gif", UnsupportedImageError),
        (b"%PDF", "private.pdf", "application/pdf", UnsupportedImageError),
        (b"heic", "photo.heic", "image/heic", UnsupportedImageError),
        (b"video", "photo.mp4", "video/mp4", UnsupportedImageError),
        (image_bytes("JPEG"), "photo.jpg", "application/octet-stream", UnsupportedImageError),
        (image_bytes("JPEG"), "photo.jpg", "image/png", UnsupportedImageError),
        (image_bytes("PNG"), "photo.jpg", "image/jpeg", UnsupportedImageError),
    ],
)
async def test_invalid_image_inputs_are_rejected_and_cleaned(
    tmp_path: Path,
    data: bytes,
    filename: str,
    content_type: str,
    expected: type[Exception],
) -> None:
    with pytest.raises(expected):
        async with temporary_image(
            upload(data, filename, content_type), base_dir=tmp_path
        ):
            pass
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_byte_and_pixel_limits_reject_and_clean_all_temp_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(image_module, "MAX_IMAGE_BYTES", 20)
    with pytest.raises(ImageTooLargeError):
        async with temporary_image(
            upload(image_bytes("JPEG"), "huge.jpg", "image/jpeg"), base_dir=tmp_path
        ):
            pass
    assert list(tmp_path.iterdir()) == []

    monkeypatch.setattr(image_module, "MAX_IMAGE_BYTES", 8 * 1024 * 1024)
    monkeypatch.setattr(image_module, "MAX_IMAGE_PIXELS", 50)
    with pytest.raises(ImagePixelLimitError):
        async with temporary_image(
            upload(image_bytes("PNG", size=(10, 10)), "bomb.png", "image/png"),
            base_dir=tmp_path,
        ):
            pass
    assert list(tmp_path.iterdir()) == []
