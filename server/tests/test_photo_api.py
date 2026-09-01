from io import BytesIO
import logging
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from PIL import Image
from sqlalchemy import func, select

from server.app.api.photo import get_vision_gateway
from server.app.api.voice import get_media_store, get_tts_gateway
from server.app.main import app
from server.app.persistence.database import SessionFactory
from server.app.photo.domain import PhotoLearningResult, RelatedWord
from server.app.photo.gateway import VisionError
from server.app.photo.model import PhotoLearningRecordModel
from server.app.voice.media import TemporaryMediaStore
from server.app.voice.tts import SynthesizedAudio, TTSError


def jpeg_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (20, 20), "red").save(output, "JPEG")
    return output.getvalue()


def headers(label: str) -> dict[str, str]:
    return {"X-Client-Id": f"photo_{label}_{uuid4().hex}"[:64]}


VALID_RESULT = PhotoLearningResult(
    status="ok",
    primary_word_en="apple",
    primary_meaning_zh="苹果",
    simple_sentence_en="This is an apple.",
    simple_sentence_zh="这是一个苹果。",
    practice_phrase="red apple",
    related_words=(RelatedWord("red", "红色"),),
    question_en="What is this?",
    encouragement_zh="很好！读一读吧。",
)


class RecordingVision:
    def __init__(self, result: PhotoLearningResult = VALID_RESULT, fail: bool = False) -> None:
        self.result = result
        self.fail = fail
        self.calls = 0
        self.path: Path | None = None
        self.prompt = ""

    async def analyze(self, *, image_path: Path, system_prompt: str) -> PhotoLearningResult:
        self.calls += 1
        self.path = image_path
        self.prompt = system_prompt
        assert image_path.exists()
        if self.fail:
            raise VisionError("raw provider response and base64-secret")
        return self.result


class RecordingTTS:
    def __init__(self, fail: bool = False) -> None:
        self.texts: list[str] = []
        self.fail = fail

    async def synthesize(self, text: str) -> SynthesizedAudio:
        self.texts.append(text)
        if self.fail:
            raise TTSError("raw provider secret")
        return SynthesizedAudio(b"RIFFphoto", "audio/wav", ".wav")


async def put_profile(client: httpx.AsyncClient, owner: dict[str, str]) -> None:
    response = await client.put(
        "/api/student/profile",
        headers=owner,
        json={"age": 8, "grade": 3, "english_level": "beginner"},
    )
    assert response.status_code == 200


async def analyze(
    client: httpx.AsyncClient,
    owner: dict[str, str],
    gateway: RecordingVision,
    *,
    setup_profile: bool = True,
) -> httpx.Response:
    app.dependency_overrides[get_vision_gateway] = lambda: gateway
    if setup_profile:
        await put_profile(client, owner)
    return await client.post(
        "/api/photo/analyze",
        headers=owner,
        files={"file": ("apple.jpg", jpeg_bytes(), "image/jpeg")},
    )


@pytest.mark.asyncio
async def test_missing_profile_short_circuits_before_vision() -> None:
    gateway = RecordingVision()
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await analyze(client, headers("missing"), gateway, setup_profile=False)
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 409
    assert gateway.calls == 0


@pytest.mark.asyncio
async def test_analysis_persists_only_safe_fields_and_cleans_temp_image() -> None:
    owner = headers("success")
    gateway = RecordingVision()
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await analyze(client, owner, gateway)
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["primary_word_en"] == "apple"
    assert body["record_id"] > 0
    assert gateway.path is not None and not gateway.path.exists()
    assert "private document" in gateway.prompt

    async with SessionFactory() as session:
        record = await session.get(PhotoLearningRecordModel, body["record_id"])
    assert record is not None and record.client_id == owner["X-Client-Id"]
    assert record.practice_phrase == "red apple"
    assert record.related_words_json == '[{"word_en":"red","meaning_zh":"红色"}]'
    column_names = set(PhotoLearningRecordModel.__table__.columns.keys())
    assert not column_names.intersection(
        {"image", "image_bytes", "image_path", "base64", "exif", "raw_provider_json", "ocr_text"}
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["unclear", "unsuitable"])
async def test_non_learning_outcomes_are_not_persisted(status: str) -> None:
    owner = headers(status)
    gateway = RecordingVision(PhotoLearningResult(status=status))
    transport = httpx.ASGITransport(app=app)
    async with SessionFactory() as session:
        before = await session.scalar(select(func.count()).select_from(PhotoLearningRecordModel))
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await analyze(client, owner, gateway)
    finally:
        app.dependency_overrides.clear()
    async with SessionFactory() as session:
        after = await session.scalar(select(func.count()).select_from(PhotoLearningRecordModel))
    assert response.status_code == 200
    assert response.json()["status"] == status
    assert response.json()["record_id"] is None
    assert response.json()["suggested_actions"] == ["retake"]
    assert before == after


@pytest.mark.asyncio
async def test_provider_error_is_safe_logged_without_payload_and_cleans_image(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING, logger="uvicorn.error.baby_english.photo")
    gateway = RecordingVision(fail=True)
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await analyze(client, headers("failure"), gateway)
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503
    assert response.json() == {"detail": "Photo English is temporarily unavailable."}
    assert "base64-secret" not in response.text
    assert "base64-secret" not in caplog.text
    assert gateway.path is not None and not gateway.path.exists()


@pytest.mark.asyncio
async def test_listen_is_owned_uses_persisted_phrase_and_reuses_voice_media(tmp_path: Path) -> None:
    owner_a, owner_b = headers("owner_a"), headers("owner_b")
    gateway, tts = RecordingVision(), RecordingTTS()
    store = TemporaryMediaStore(base_dir=tmp_path)
    app.dependency_overrides.update(
        {
            get_vision_gateway: lambda: gateway,
            get_tts_gateway: lambda: tts,
            get_media_store: lambda: store,
        }
    )
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await put_profile(client, owner_a)
            await put_profile(client, owner_b)
            created = await client.post(
                "/api/photo/analyze",
                headers=owner_a,
                files={"file": ("apple.jpg", jpeg_bytes(), "image/jpeg")},
            )
            record_id = created.json()["record_id"]
            denied = await client.post(f"/api/photo/records/{record_id}/listen", headers=owner_b)
            heard = await client.post(
                f"/api/photo/records/{record_id}/listen",
                headers=owner_a,
                json={"text": "speak this arbitrary secret"},
            )
            media = await client.get(heard.json()["audio_url"])
    finally:
        app.dependency_overrides.clear()
        store.cleanup()
    assert denied.status_code == 404
    assert heard.status_code == 200
    assert heard.json()["audio_url"].startswith("/api/voice/media/")
    assert media.content == b"RIFFphoto"
    assert tts.texts == ["red apple"]


@pytest.mark.asyncio
async def test_listen_tts_error_is_safe(tmp_path: Path) -> None:
    owner = headers("tts_error")
    gateway, tts = RecordingVision(), RecordingTTS(fail=True)
    store = TemporaryMediaStore(base_dir=tmp_path)
    app.dependency_overrides.update(
        {
            get_vision_gateway: lambda: gateway,
            get_tts_gateway: lambda: tts,
            get_media_store: lambda: store,
        }
    )
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await put_profile(client, owner)
            created = await client.post(
                "/api/photo/analyze",
                headers=owner,
                files={"file": ("apple.jpg", jpeg_bytes(), "image/jpeg")},
            )
            response = await client.post(
                f"/api/photo/records/{created.json()['record_id']}/listen",
                headers=owner,
            )
    finally:
        app.dependency_overrides.clear()
        store.cleanup()
    assert response.status_code == 503
    assert "raw provider" not in response.text
