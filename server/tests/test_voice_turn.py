from pathlib import Path

import httpx
import pytest

from server.app.api.tutor import get_tutor_service
from server.app.api.voice import (
    get_media_store,
    get_stt_gateway,
    get_tts_gateway,
)
from server.app.main import app
from server.app.tutor.service import TutorService
from server.app.voice.media import TemporaryMediaStore
from server.app.voice.stt import Transcript
from server.app.voice.tts import (
    FakeTTS,
    SynthesizedAudio,
    TTSError,
    create_tts,
)


class RecordingSTT:
    def __init__(self) -> None:
        self.audio_path: Path | None = None

    async def transcribe(self, audio_path: Path) -> Transcript:
        assert audio_path.exists()
        self.audio_path = audio_path
        return Transcript(text="苹果英文怎么说", duration_ms=1830)


class RecordingLLM:
    def __init__(self) -> None:
        self.message = ""
        self.system_prompt = ""

    async def generate(self, *, system_prompt: str, message: str) -> str:
        self.message = message
        self.system_prompt = system_prompt
        return "Apple 🍎. Repeat after me: apple."


class RecordingTTS:
    def __init__(self) -> None:
        self.text = ""

    async def synthesize(self, text: str) -> SynthesizedAudio:
        self.text = text
        return SynthesizedAudio(
            data=b"RIFFmock-wave",
            content_type="audio/wav",
            extension=".wav",
        )


class FailingTTS(RecordingTTS):
    async def synthesize(self, text: str) -> SynthesizedAudio:
        self.text = text
        raise TTSError("provider raw error")


def set_voice_overrides(
    *,
    stt: RecordingSTT,
    llm: RecordingLLM,
    tts,
    store: TemporaryMediaStore,
) -> None:
    app.dependency_overrides[get_stt_gateway] = lambda: stt
    app.dependency_overrides[get_tutor_service] = lambda: TutorService(llm=llm)
    app.dependency_overrides[get_tts_gateway] = lambda: tts
    app.dependency_overrides[get_media_store] = lambda: store


@pytest.mark.asyncio
async def test_batch_voice_turn_runs_stt_tutor_llm_tts_and_media(tmp_path: Path) -> None:
    stt = RecordingSTT()
    llm = RecordingLLM()
    tts = RecordingTTS()
    store = TemporaryMediaStore(base_dir=tmp_path)
    set_voice_overrides(stt=stt, llm=llm, tts=tts, store=store)
    transport = httpx.ASGITransport(app=app)

    try:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/voice/turn",
                data={"age": "8", "grade": "3", "english_level": "beginner"},
                files={"file": ("recording.mp3", b"mock audio", "audio/mpeg")},
            )
            audio_response = await client.get(response.json()["audio_url"])
    finally:
        app.dependency_overrides.clear()
        store.cleanup()

    assert response.status_code == 200
    assert response.json() == {
        "transcript": "苹果英文怎么说",
        "reply": "Apple 🍎. Repeat after me: apple.",
        "audio_url": response.json()["audio_url"],
        "suggested_actions": ["listen", "repeat", "explain_zh"],
    }
    assert response.json()["audio_url"].startswith("/api/voice/media/")
    assert audio_response.status_code == 200
    assert audio_response.content == b"RIFFmock-wave"
    assert audio_response.headers["content-type"].startswith("audio/wav")
    assert stt.audio_path is not None
    assert not stt.audio_path.exists()
    assert llm.message == "苹果英文怎么说"
    assert "beginner" in llm.system_prompt
    assert tts.text == "Apple 🍎. Repeat after me: apple."


@pytest.mark.asyncio
async def test_voice_turn_provider_failure_is_safe_and_cleans_temp(
    tmp_path: Path,
) -> None:
    stt = RecordingSTT()
    store = TemporaryMediaStore(base_dir=tmp_path)
    set_voice_overrides(
        stt=stt,
        llm=RecordingLLM(),
        tts=FailingTTS(),
        store=store,
    )
    transport = httpx.ASGITransport(app=app)

    try:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/voice/turn",
                data={"age": "8", "grade": "3", "english_level": "beginner"},
                files={"file": ("recording.mp3", b"mock audio", "audio/mpeg")},
            )
    finally:
        app.dependency_overrides.clear()
        store.cleanup()

    assert response.status_code == 503
    assert response.json() == {"detail": "Voice tutor is temporarily unavailable."}
    assert "provider raw error" not in response.text
    assert stt.audio_path is not None
    assert not stt.audio_path.exists()


@pytest.mark.asyncio
async def test_fake_tts_needs_no_key_and_returns_valid_wav(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TTS_PROVIDER", raising=False)

    tts = create_tts()
    audio = await tts.synthesize("Hello")

    assert isinstance(tts, FakeTTS)
    assert audio.content_type == "audio/wav"
    assert audio.data.startswith(b"RIFF")


@pytest.mark.asyncio
async def test_temporary_media_expires_and_is_deleted(tmp_path: Path) -> None:
    store = TemporaryMediaStore(base_dir=tmp_path, ttl_seconds=0)
    media_id = store.save(
        SynthesizedAudio(
            data=b"RIFFmock-wave",
            content_type="audio/wav",
            extension=".wav",
        )
    )

    assert store.get(media_id) is None
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value"),
    [("age", "4"), ("age", "16"), ("grade", "0"), ("grade", "10")],
)
async def test_voice_turn_rejects_invalid_student_range_before_stt(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    stt = RecordingSTT()
    store = TemporaryMediaStore(base_dir=tmp_path)
    set_voice_overrides(
        stt=stt,
        llm=RecordingLLM(),
        tts=RecordingTTS(),
        store=store,
    )
    transport = httpx.ASGITransport(app=app)
    form_data = {
        "age": "8",
        "grade": "3",
        "english_level": "beginner",
        field: value,
    }

    try:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/voice/turn",
                data=form_data,
                files={"file": ("recording.mp3", b"mock audio", "audio/mpeg")},
            )
    finally:
        app.dependency_overrides.clear()
        store.cleanup()

    assert response.status_code == 422
    assert stt.audio_path is None
