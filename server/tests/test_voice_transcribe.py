from pathlib import Path

import httpx
import pytest

import server.app.voice.audio as audio_module
from server.app.api.voice import get_stt_gateway
from server.app.main import app
from server.app.voice.stt import STTError, Transcript


class RecordingSTT:
    def __init__(self) -> None:
        self.audio_path: Path | None = None

    async def transcribe(self, audio_path: Path) -> Transcript:
        assert audio_path.exists()
        self.audio_path = audio_path
        return Transcript(text="苹果英文怎么说", duration_ms=1830)


class FailingSTT(RecordingSTT):
    async def transcribe(self, audio_path: Path) -> Transcript:
        self.audio_path = audio_path
        raise STTError("provider raw error")


async def post_audio(
    gateway,
    *,
    content: bytes,
    filename: str = "recording.mp3",
    content_type: str = "audio/mpeg",
) -> httpx.Response:
    app.dependency_overrides[get_stt_gateway] = lambda: gateway
    transport = httpx.ASGITransport(app=app)

    try:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            return await client.post(
                "/api/voice/transcribe",
                headers={"X-Client-Id": "test_transcribe_client_00000001"},
                files={"file": (filename, content, content_type)},
            )
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_valid_audio_returns_fake_transcript_and_cleans_temp() -> None:
    gateway = RecordingSTT()

    response = await post_audio(gateway, content=b"mock mp3 audio")

    assert response.status_code == 200
    assert response.json() == {
        "text": "苹果英文怎么说",
        "duration_ms": 1830,
    }
    assert gateway.audio_path is not None
    assert not gateway.audio_path.exists()


@pytest.mark.asyncio
async def test_empty_audio_returns_4xx() -> None:
    response = await post_audio(RecordingSTT(), content=b"")

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_oversized_audio_returns_4xx(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(audio_module, "MAX_AUDIO_BYTES", 4)

    response = await post_audio(RecordingSTT(), content=b"12345")

    assert response.status_code == 413


@pytest.mark.asyncio
async def test_unsupported_audio_returns_4xx() -> None:
    response = await post_audio(
        RecordingSTT(),
        content=b"not audio",
        filename="recording.txt",
        content_type="text/plain",
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_stt_failure_is_mapped_and_temp_is_cleaned() -> None:
    gateway = FailingSTT()

    response = await post_audio(gateway, content=b"mock mp3 audio")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Speech recognition is temporarily unavailable."
    }
    assert "provider raw error" not in response.text
    assert gateway.audio_path is not None
    assert not gateway.audio_path.exists()
