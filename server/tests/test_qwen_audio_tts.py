import pytest
from dashscope.audio.tts_v2 import AudioFormat

import server.app.voice.tts as tts_module
from server.app.voice.tts import (
    QwenAudioTTS,
    TTSConfigurationError,
    TTSError,
    build_qwen_tts_websocket_url,
    create_tts,
)


class MockSynthesizer:
    def __init__(self, *, audio: bytes = b"ID3mock-mp3", error=None, **configuration):
        self.audio = audio
        self.error = error
        self.configuration = configuration
        self.call_request = None

    def call(self, text: str, timeout_millis: int):
        self.call_request = {
            "text": text,
            "timeout_millis": timeout_millis,
        }
        if self.error is not None:
            raise self.error
        return self.audio


def set_qwen_tts_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("TTS_PROVIDER", "qwen_audio")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setenv("DASHSCOPE_WORKSPACE_ID", "workspace-123")
    monkeypatch.setenv("DASHSCOPE_REGION", "cn-beijing")
    monkeypatch.setenv("TTS_MODEL", "qwen-audio-3.0-tts-flash")
    monkeypatch.setenv("TTS_VOICE", "longanhuan_v3.6")
    monkeypatch.setenv("TTS_SPEED", "0.9")
    monkeypatch.setenv("TTS_TIMEOUT", "60")


def test_qwen_tts_beijing_websocket_url() -> None:
    assert build_qwen_tts_websocket_url("workspace-123", "cn-beijing") == (
        "wss://workspace-123.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference"
    )


def test_factory_selects_qwen_tts_and_maps_shared_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_qwen_tts_environment(monkeypatch)

    tts = create_tts()

    assert isinstance(tts, QwenAudioTTS)
    assert tts.model == "qwen-audio-3.0-tts-flash"
    assert tts.voice == "longanhuan_v3.6"
    assert tts.speed == 0.9
    assert tts.timeout == 60
    assert tts.websocket_url == (
        "wss://workspace-123.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference"
    )
    assert "test-key" not in repr(tts)


@pytest.mark.asyncio
async def test_qwen_tts_maps_sdk_request_and_returns_mp3(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}

    def factory(**configuration):
        synthesizer = MockSynthesizer(**configuration)
        captured["synthesizer"] = synthesizer
        captured["dashscope_api_key"] = tts_module.dashscope.api_key
        return synthesizer

    monkeypatch.setattr(tts_module.dashscope, "api_key", "previous-key")
    tts = QwenAudioTTS(
        websocket_url=(
            "wss://workspace-123.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference"
        ),
        workspace_id="workspace-123",
        api_key="test-key",
        model="qwen-audio-3.0-tts-flash",
        voice="longanhuan_v3.6",
        speed=0.9,
        timeout=60,
        synthesizer_factory=factory,
    )

    audio = await tts.synthesize("Banana. Repeat after me: banana.")

    synthesizer = captured["synthesizer"]
    assert captured["dashscope_api_key"] == "test-key"
    assert tts_module.dashscope.api_key == "previous-key"
    assert synthesizer.configuration == {
        "model": "qwen-audio-3.0-tts-flash",
        "voice": "longanhuan_v3.6",
        "format": AudioFormat.MP3_24000HZ_MONO_256KBPS,
        "speech_rate": 0.9,
        "workspace": "workspace-123",
        "url": (
            "wss://workspace-123.cn-beijing.maas.aliyuncs.com"
            "/api-ws/v1/inference"
        ),
    }
    assert synthesizer.call_request == {
        "text": "Banana. Repeat after me: banana.",
        "timeout_millis": 60000,
    }
    assert audio.data == b"ID3mock-mp3"
    assert audio.content_type == "audio/mpeg"
    assert audio.extension == ".mp3"


@pytest.mark.asyncio
async def test_qwen_tts_provider_error_is_normalized() -> None:
    tts = QwenAudioTTS(
        websocket_url="wss://provider.test/api-ws/v1/inference",
        workspace_id="workspace-123",
        api_key="test-key",
        model="qwen-audio-3.0-tts-flash",
        synthesizer_factory=lambda **configuration: MockSynthesizer(
            error=TimeoutError("provider raw timeout"),
            **configuration,
        ),
    )

    with pytest.raises(TTSError, match="provider request failed"):
        await tts.synthesize("hello")


@pytest.mark.asyncio
async def test_qwen_tts_empty_audio_is_rejected() -> None:
    tts = QwenAudioTTS(
        websocket_url="wss://provider.test/api-ws/v1/inference",
        workspace_id="workspace-123",
        api_key="test-key",
        model="qwen-audio-3.0-tts-flash",
        synthesizer_factory=lambda **configuration: MockSynthesizer(
            audio=b"",
            **configuration,
        ),
    )

    with pytest.raises(TTSError, match="empty audio"):
        await tts.synthesize("hello")


@pytest.mark.parametrize(
    "missing_variable",
    ["DASHSCOPE_API_KEY", "DASHSCOPE_WORKSPACE_ID", "TTS_MODEL"],
)
def test_qwen_tts_missing_configuration_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    missing_variable: str,
) -> None:
    set_qwen_tts_environment(monkeypatch)
    monkeypatch.delenv(missing_variable)

    with pytest.raises(TTSConfigurationError, match=missing_variable):
        create_tts()
