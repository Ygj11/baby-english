import mimetypes
import os
from pathlib import Path

import pytest
from starlette.datastructures import Headers, UploadFile

from server.app.photo.gateway import create_vision_gateway
from server.app.photo.image import temporary_image
from server.app.photo.qwen import QwenVision
from server.app.photo.service import PhotoLearningService
from server.app.tutor.schemas import StudentProfile


@pytest.mark.real_provider
@pytest.mark.asyncio
async def test_qwen_vision_real_provider_returns_normalized_lesson() -> None:
    if os.getenv("RUN_REAL_PROVIDER_TESTS") != "1":
        pytest.skip("Set RUN_REAL_PROVIDER_TESTS=1 for real provider integration.")
    raw_path = os.getenv("REAL_VISION_IMAGE_PATH", "").strip()
    if not raw_path:
        pytest.skip("Set REAL_VISION_IMAGE_PATH to an external JPEG/PNG/WebP fixture.")
    image_path = Path(raw_path).expanduser().resolve()
    repository_root = Path(__file__).resolve().parents[2]
    if not image_path.is_file():
        pytest.skip("REAL_VISION_IMAGE_PATH does not point to a readable file.")
    if image_path.is_relative_to(repository_root):
        pytest.skip("REAL_VISION_IMAGE_PATH must be outside the repository.")

    content_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
    gateway = create_vision_gateway("qwen")
    assert isinstance(gateway, QwenVision)
    with image_path.open("rb") as source:
        upload = UploadFile(
            source,
            filename=image_path.name,
            headers=Headers({"content-type": content_type}),
        )
        async with temporary_image(upload) as normalized:
            result = await PhotoLearningService(gateway).analyze(
                image_path=normalized.path,
                student=StudentProfile(age=8, grade=3, english_level="beginner"),
            )
    assert result.status in {"ok", "unclear", "unsuitable"}
    if result.status == "ok":
        assert result.primary_word_en
        assert result.practice_phrase
