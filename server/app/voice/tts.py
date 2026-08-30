"""Batch TTS gateway boundary."""

import asyncio
import io
import os
import re
import threading
import wave
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx
import dashscope
from dashscope.audio.tts_v2 import AudioFormat, SpeechSynthesizer

from server.app.provider_environment import (
    ProviderEnvironmentError,
    ensure_fake_provider_allowed,
)


class TTSError(RuntimeError):
    """Normalized TTS provider failure."""


class TTSConfigurationError(TTSError):
    """Raised when the configured TTS provider has no adapter."""


@dataclass(frozen=True, slots=True)
class SynthesizedAudio:
    data: bytes
    content_type: str
    extension: str


class TTSGateway(Protocol):
    async def synthesize(self, text: str) -> SynthesizedAudio:
        """Synthesize one complete batch reply."""


class FakeTTS:
    """No-key TTS that returns a short valid WAV placeholder."""

    async def synthesize(self, text: str) -> SynthesizedAudio:
        return SynthesizedAudio(
            data=_build_silent_wav(),
            content_type="audio/wav",
            extension=".wav",
        )


@dataclass(slots=True)
class MiniMaxTTS:
    """Non-streaming MiniMax T2A adapter returning decoded MP3 bytes."""

    endpoint: str
    api_key: str = field(repr=False)
    model: str
    voice_id: str
    speed: float = 0.9
    timeout: float = 60.0
    client: Any | None = field(default=None, repr=False)

    async def synthesize(self, text: str) -> SynthesizedAudio:
        payload = {
            "model": self.model,
            "text": text,
            "stream": False,
            "voice_setting": {
                "voice_id": self.voice_id,
                "speed": self.speed,
            },
            "audio_setting": {
                "format": "mp3",
                "channel": 1,
            },
            "output_format": "hex",
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            if self.client is not None:
                response = await self.client.post(
                    self.endpoint,
                    headers=headers,
                    json=payload,
                )
            else:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.endpoint,
                        headers=headers,
                        json=payload,
                    )
            response.raise_for_status()
            response_data = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise TTSError("The TTS provider request failed.") from error

        try:
            status_code = response_data["base_resp"]["status_code"]
            encoded_audio = response_data["data"]["audio"]
        except (KeyError, TypeError) as error:
            raise TTSError("The TTS provider returned an invalid response.") from error

        if status_code != 0:
            raise TTSError("The TTS provider rejected the request.")
        if not isinstance(encoded_audio, str) or not encoded_audio.strip():
            raise TTSError("The TTS provider returned empty audio.")
        try:
            audio_data = bytes.fromhex(encoded_audio)
        except ValueError as error:
            raise TTSError("The TTS provider returned invalid audio.") from error
        if not audio_data:
            raise TTSError("The TTS provider returned empty audio.")

        return SynthesizedAudio(
            data=audio_data,
            content_type="audio/mpeg",
            extension=".mp3",
        )


_dashscope_configuration_lock = threading.Lock()


@dataclass(slots=True)
class QwenAudioTTS:
    """Thin async adapter over DashScope's official Qwen Audio TTS SDK."""

    websocket_url: str
    workspace_id: str
    api_key: str = field(repr=False)
    model: str
    voice: str = "longanhuan_v3.6"
    speed: float = 0.9
    timeout: float = 60.0
    synthesizer_factory: Any = field(default=SpeechSynthesizer, repr=False)

    async def synthesize(self, text: str) -> SynthesizedAudio:
        try:
            audio_data = await asyncio.to_thread(self._synthesize_sync, text)
        except Exception as error:
            raise TTSError("The TTS provider request failed.") from error

        if not isinstance(audio_data, bytes) or not audio_data:
            raise TTSError("The TTS provider returned empty audio.")
        return SynthesizedAudio(
            data=audio_data,
            content_type="audio/mpeg",
            extension=".mp3",
        )

    def _synthesize_sync(self, text: str) -> bytes:
        with _dashscope_configuration_lock:
            previous_api_key = dashscope.api_key
            try:
                dashscope.api_key = self.api_key
                synthesizer = self.synthesizer_factory(
                    model=self.model,
                    voice=self.voice,
                    format=AudioFormat.MP3_24000HZ_MONO_256KBPS,
                    speech_rate=self.speed,
                    workspace=self.workspace_id,
                    url=self.websocket_url,
                )
            finally:
                dashscope.api_key = previous_api_key

        return synthesizer.call(
            text,
            timeout_millis=round(self.timeout * 1000),
        )


def create_tts(provider: str | None = None) -> TTSGateway:
    """Create the configured batch TTS adapter without choosing a vendor."""
    selected_provider = provider
    if selected_provider is None:
        selected_provider = os.getenv("TTS_PROVIDER", "")

    try:
        ensure_fake_provider_allowed(selected_provider)
    except ProviderEnvironmentError as error:
        raise TTSConfigurationError(str(error)) from error

    normalized_provider = selected_provider.strip().lower()
    if normalized_provider in {"", "fake"}:
        return FakeTTS()

    if normalized_provider == "minimax":
        return MiniMaxTTS(
            endpoint=_required_environment("MINIMAX_BASE_URL"),
            api_key=_required_environment("MINIMAX_API_KEY"),
            model=_required_environment("TTS_MODEL"),
            voice_id=_required_environment("MINIMAX_VOICE_ID"),
            speed=_positive_float_environment("TTS_SPEED", default=0.9),
            timeout=_positive_float_environment("TTS_TIMEOUT", default=60.0),
        )

    if normalized_provider == "qwen_audio":
        workspace_id = _required_environment("DASHSCOPE_WORKSPACE_ID")
        region = os.getenv("DASHSCOPE_REGION", "cn-beijing").strip()
        return QwenAudioTTS(
            websocket_url=build_qwen_tts_websocket_url(workspace_id, region),
            workspace_id=workspace_id,
            api_key=_required_environment("DASHSCOPE_API_KEY"),
            model=_required_environment("TTS_MODEL"),
            voice=os.getenv("TTS_VOICE", "longanhuan_v3.6").strip()
            or "longanhuan_v3.6",
            speed=_positive_float_environment("TTS_SPEED", default=0.9),
            timeout=_positive_float_environment("TTS_TIMEOUT", default=60.0),
        )

    raise TTSConfigurationError("The configured TTS provider is unavailable.")


def build_qwen_tts_websocket_url(workspace_id: str, region: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9-]+", workspace_id):
        raise TTSConfigurationError("DASHSCOPE_WORKSPACE_ID is invalid.")
    if not re.fullmatch(r"[a-z0-9-]+", region):
        raise TTSConfigurationError("DASHSCOPE_REGION is invalid.")
    return (
        f"wss://{workspace_id}.{region}.maas.aliyuncs.com"
        "/api-ws/v1/inference"
    )


def _required_environment(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise TTSConfigurationError(f"{name} is required for the configured TTS.")
    return value


def _positive_float_environment(name: str, *, default: float) -> float:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        value = float(raw_value)
    except ValueError as error:
        raise TTSConfigurationError(f"{name} must be a positive number.") from error
    if value <= 0:
        raise TTSConfigurationError(f"{name} must be a positive number.")
    return value


def _build_silent_wav() -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(1)
        wav_file.setframerate(8000)
        wav_file.writeframes(b"\x80" * 800)
    return buffer.getvalue()
