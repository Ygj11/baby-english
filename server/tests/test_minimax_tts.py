import json

import httpx
import pytest

from server.app.voice.tts import (
    FakeTTS,
    MiniMaxTTS,
    TTSConfigurationError,
    TTSError,
    create_tts,
)


def make_adapter(transport: httpx.AsyncBaseTransport) -> MiniMaxTTS:
    return MiniMaxTTS(
        endpoint="https://api.minimaxi.com/v1/t2a_v2",
        api_key="test-key",
        model="speech-2.8-turbo",
        voice_id="owner-selected-voice",
        speed=0.9,
        timeout=60,
        client=httpx.AsyncClient(transport=transport),
    )


@pytest.mark.asyncio
async def test_request_mapping_and_hex_mp3_response() -> None:
    mp3_bytes = b"ID3mock-mp3"
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = request.headers
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "base_resp": {"status_code": 0, "status_msg": "success"},
                "data": {"audio": mp3_bytes.hex()},
            },
        )

    adapter = make_adapter(httpx.MockTransport(handler))
    try:
        audio = await adapter.synthesize("Apple. Repeat after me: apple.")
    finally:
        await adapter.client.aclose()

    assert captured["headers"]["authorization"] == "Bearer test-key"
    assert captured["payload"] == {
        "model": "speech-2.8-turbo",
        "text": "Apple. Repeat after me: apple.",
        "stream": False,
        "voice_setting": {
            "voice_id": "owner-selected-voice",
            "speed": 0.9,
        },
        "audio_setting": {
            "format": "mp3",
            "channel": 1,
        },
        "output_format": "hex",
    }
    assert audio.data == mp3_bytes
    assert audio.content_type == "audio/mpeg"
    assert audio.extension == ".mp3"


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [401, 403, 500])
async def test_http_errors_are_normalized(status_code: int) -> None:
    adapter = make_adapter(
        httpx.MockTransport(lambda request: httpx.Response(status_code))
    )
    try:
        with pytest.raises(TTSError, match="provider request failed"):
            await adapter.synthesize("hello")
    finally:
        await adapter.client.aclose()


@pytest.mark.asyncio
async def test_timeout_is_normalized() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    adapter = make_adapter(httpx.MockTransport(handler))
    try:
        with pytest.raises(TTSError, match="provider request failed"):
            await adapter.synthesize("hello")
    finally:
        await adapter.client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response_data",
    [
        {},
        {"base_resp": {"status_code": 1001}, "data": {"audio": "494433"}},
        {"base_resp": {"status_code": 0}, "data": {"audio": ""}},
        {"base_resp": {"status_code": 0}, "data": {"audio": "not-hex"}},
    ],
)
async def test_provider_error_or_invalid_audio_is_normalized(
    response_data: dict,
) -> None:
    adapter = make_adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=response_data))
    )
    try:
        with pytest.raises(TTSError):
            await adapter.synthesize("hello")
    finally:
        await adapter.client.aclose()


def set_real_tts_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("TTS_PROVIDER", "minimax")
    monkeypatch.setenv("MINIMAX_API_KEY", "test-key")
    monkeypatch.setenv("MINIMAX_BASE_URL", "https://api.minimaxi.com/v1/t2a_v2")
    monkeypatch.setenv("TTS_MODEL", "speech-2.8-turbo")
    monkeypatch.setenv("MINIMAX_VOICE_ID", "owner-selected-voice")
    monkeypatch.setenv("TTS_SPEED", "0.9")
    monkeypatch.setenv("TTS_TIMEOUT", "60")


def test_factory_selects_minimax_and_maps_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_real_tts_environment(monkeypatch)

    adapter = create_tts()

    assert isinstance(adapter, MiniMaxTTS)
    assert adapter.endpoint == "https://api.minimaxi.com/v1/t2a_v2"
    assert adapter.model == "speech-2.8-turbo"
    assert adapter.voice_id == "owner-selected-voice"
    assert adapter.speed == 0.9
    assert adapter.timeout == 60
    assert "test-key" not in repr(adapter)


@pytest.mark.parametrize(
    "missing_variable",
    ["MINIMAX_API_KEY", "MINIMAX_BASE_URL", "TTS_MODEL", "MINIMAX_VOICE_ID"],
)
def test_missing_real_configuration_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    missing_variable: str,
) -> None:
    set_real_tts_environment(monkeypatch)
    monkeypatch.delenv(missing_variable)

    with pytest.raises(TTSConfigurationError, match=missing_variable):
        create_tts()


def test_fake_factory_still_works(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("TTS_PROVIDER", "fake")

    assert isinstance(create_tts(), FakeTTS)
