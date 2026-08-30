import base64
import json
from pathlib import Path

import httpx
import pytest

from server.app.voice.stt import (
    FakeSTT,
    QwenAudioSTT,
    STTConfigurationError,
    STTError,
    build_qwen_audio_endpoint,
    create_stt,
)


def make_adapter(transport: httpx.AsyncBaseTransport) -> QwenAudioSTT:
    return QwenAudioSTT(
        endpoint=build_qwen_audio_endpoint("workspace-123", "cn-beijing"),
        api_key="test-key",
        model="qwen-audio-3.0-asr-flash",
        language_hints=("zh", "en"),
        timeout=60,
        client=httpx.AsyncClient(transport=transport),
    )


def test_beijing_endpoint_generation() -> None:
    assert build_qwen_audio_endpoint("workspace-123", "cn-beijing") == (
        "https://workspace-123.cn-beijing.maas.aliyuncs.com"
        "/api/v1/services/aigc/multimodal-generation/generation"
    )


@pytest.mark.asyncio
async def test_mp3_maps_to_data_uri_hints_and_transcript(tmp_path: Path) -> None:
    audio = b"mock mp3 bytes"
    audio_path = tmp_path / "recording.mp3"
    audio_path.write_bytes(audio)
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = request.headers
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "output": {"text": "苹果英文怎么说"},
                "usage": {"duration": 1.83},
            },
        )

    adapter = make_adapter(httpx.MockTransport(handler))
    try:
        transcript = await adapter.transcribe(audio_path)
    finally:
        await adapter.client.aclose()

    expected_audio = base64.b64encode(audio).decode("ascii")
    assert transcript.text == "苹果英文怎么说"
    assert transcript.duration_ms == 1830
    assert captured["headers"]["authorization"] == "Bearer test-key"
    assert captured["headers"]["x-dashscope-sse"] == "disable"
    assert captured["payload"] == {
        "model": "qwen-audio-3.0-asr-flash",
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": f"data:audio/mpeg;base64,{expected_audio}"
                            },
                        }
                    ],
                }
            ]
        },
        "parameters": {
            "format": "mp3",
            "sample_rate": "16000",
            "language_hints": ["zh", "en"],
        },
    }


@pytest.mark.asyncio
async def test_wav_keeps_its_real_format(tmp_path: Path) -> None:
    audio_path = tmp_path / "recording.wav"
    audio_path.write_bytes(b"RIFFmock")
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={"output": {"text": "hello"}, "usage": {"duration": 1}},
        )

    adapter = make_adapter(httpx.MockTransport(handler))
    try:
        await adapter.transcribe(audio_path)
    finally:
        await adapter.client.aclose()

    assert captured["parameters"]["format"] == "wav"
    data_uri = captured["input"]["messages"][0]["content"][0]["input_audio"]["data"]
    assert data_uri.startswith("data:audio/wav;base64,")


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [401, 403, 500])
async def test_provider_http_errors_are_normalized(
    tmp_path: Path,
    status_code: int,
) -> None:
    audio_path = tmp_path / "recording.mp3"
    audio_path.write_bytes(b"audio")
    adapter = make_adapter(
        httpx.MockTransport(lambda request: httpx.Response(status_code))
    )

    try:
        with pytest.raises(STTError, match="provider request failed"):
            await adapter.transcribe(audio_path)
    finally:
        await adapter.client.aclose()


@pytest.mark.asyncio
async def test_timeout_is_normalized(tmp_path: Path) -> None:
    audio_path = tmp_path / "recording.mp3"
    audio_path.write_bytes(b"audio")

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    adapter = make_adapter(httpx.MockTransport(handler))
    try:
        with pytest.raises(STTError, match="provider request failed"):
            await adapter.transcribe(audio_path)
    finally:
        await adapter.client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response_data",
    [
        {},
        {"output": {"text": ""}, "usage": {"duration": 1}},
        {"output": {"text": "hello"}, "usage": {}},
    ],
)
async def test_malformed_or_empty_response_is_normalized(
    tmp_path: Path,
    response_data: dict,
) -> None:
    audio_path = tmp_path / "recording.mp3"
    audio_path.write_bytes(b"audio")
    adapter = make_adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=response_data))
    )

    try:
        with pytest.raises(STTError):
            await adapter.transcribe(audio_path)
    finally:
        await adapter.client.aclose()


@pytest.mark.asyncio
async def test_unsupported_audio_is_not_disguised_as_mp3(tmp_path: Path) -> None:
    audio_path = tmp_path / "recording.m4a"
    audio_path.write_bytes(b"audio")
    adapter = make_adapter(httpx.MockTransport(lambda request: httpx.Response(200)))

    try:
        with pytest.raises(STTError, match="only MP3 and WAV"):
            await adapter.transcribe(audio_path)
    finally:
        await adapter.client.aclose()


def set_real_stt_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("STT_PROVIDER", "qwen_audio")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setenv("DASHSCOPE_WORKSPACE_ID", "workspace-123")
    monkeypatch.setenv("DASHSCOPE_REGION", "cn-beijing")
    monkeypatch.setenv("STT_MODEL", "qwen-audio-3.0-asr-flash")
    monkeypatch.setenv("STT_LANGUAGE_HINTS", "zh,en")
    monkeypatch.setenv("STT_TIMEOUT", "60")


def test_factory_selects_qwen_and_maps_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_real_stt_environment(monkeypatch)

    adapter = create_stt()

    assert isinstance(adapter, QwenAudioSTT)
    assert adapter.endpoint.startswith("https://workspace-123.cn-beijing.")
    assert adapter.model == "qwen-audio-3.0-asr-flash"
    assert adapter.language_hints == ("zh", "en")
    assert adapter.timeout == 60
    assert "test-key" not in repr(adapter)


@pytest.mark.parametrize("missing_variable", ["DASHSCOPE_API_KEY", "DASHSCOPE_WORKSPACE_ID", "STT_MODEL"])
def test_missing_real_configuration_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    missing_variable: str,
) -> None:
    set_real_stt_environment(monkeypatch)
    monkeypatch.delenv(missing_variable)

    with pytest.raises(STTConfigurationError, match=missing_variable):
        create_stt()


def test_fake_factory_still_works(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("STT_PROVIDER", "fake")

    assert isinstance(create_stt(), FakeSTT)
