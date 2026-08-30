"""Batch STT gateway boundary."""

import base64
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import httpx

from server.app.provider_environment import (
    ProviderEnvironmentError,
    ensure_fake_provider_allowed,
)


class STTError(RuntimeError):
    """Normalized STT provider failure."""


class STTConfigurationError(STTError):
    """Raised when the configured STT provider has no adapter."""


@dataclass(frozen=True, slots=True)
class Transcript:
    text: str
    duration_ms: int


class STTGateway(Protocol):
    async def transcribe(self, audio_path: Path) -> Transcript:
        """Transcribe one validated temporary audio file."""


@dataclass(slots=True)
class FakeSTT:
    fixed_text: str = "苹果英文怎么说"
    duration_ms: int = 1000

    async def transcribe(self, audio_path: Path) -> Transcript:
        return Transcript(text=self.fixed_text, duration_ms=self.duration_ms)


@dataclass(slots=True)
class QwenAudioSTT:
    """Batch Qwen Audio adapter using an inline Base64 Data URI."""

    endpoint: str
    api_key: str = field(repr=False)
    model: str = "qwen-audio-3.0-asr-flash"
    language_hints: tuple[str, ...] = ("zh", "en")
    timeout: float = 60.0
    client: Any | None = field(default=None, repr=False)

    async def transcribe(self, audio_path: Path) -> Transcript:
        audio_format, media_type = _audio_format(audio_path)
        try:
            audio_data = audio_path.read_bytes()
        except OSError as error:
            raise STTError("The audio file could not be read.") from error

        payload = {
            "model": self.model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_audio",
                                "input_audio": {
                                    "data": (
                                        f"data:{media_type};base64,"
                                        f"{base64.b64encode(audio_data).decode('ascii')}"
                                    )
                                },
                            }
                        ],
                    }
                ]
            },
            "parameters": {
                "format": audio_format,
                "sample_rate": "16000",
                "language_hints": list(self.language_hints),
            },
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-SSE": "disable",
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
            raise STTError("The STT provider request failed.") from error

        try:
            text = response_data["output"]["text"]
            duration_seconds = response_data["usage"]["duration"]
            duration_ms = round(float(duration_seconds) * 1000)
        except (KeyError, TypeError, ValueError, OverflowError) as error:
            raise STTError("The STT provider returned an invalid response.") from error

        if not isinstance(text, str) or not text.strip():
            raise STTError("The STT provider returned an empty transcript.")
        if duration_ms < 0:
            raise STTError("The STT provider returned an invalid duration.")
        return Transcript(text=text.strip(), duration_ms=duration_ms)


def create_stt(provider: str | None = None) -> STTGateway:
    """Create the configured batch STT adapter without choosing a vendor."""
    selected_provider = provider
    if selected_provider is None:
        selected_provider = os.getenv("STT_PROVIDER", "")

    try:
        ensure_fake_provider_allowed(selected_provider)
    except ProviderEnvironmentError as error:
        raise STTConfigurationError(str(error)) from error

    normalized_provider = selected_provider.strip().lower()
    if normalized_provider in {"", "fake"}:
        return FakeSTT()

    if normalized_provider == "qwen_audio":
        api_key = _required_environment("DASHSCOPE_API_KEY")
        workspace_id = _required_environment("DASHSCOPE_WORKSPACE_ID")
        region = os.getenv("DASHSCOPE_REGION", "cn-beijing").strip()
        model = _required_environment("STT_MODEL")
        language_hints = _language_hints(
            os.getenv("STT_LANGUAGE_HINTS", "zh,en")
        )
        timeout = _positive_float_environment("STT_TIMEOUT", default=60.0)
        return QwenAudioSTT(
            endpoint=build_qwen_audio_endpoint(workspace_id, region),
            api_key=api_key,
            model=model,
            language_hints=language_hints,
            timeout=timeout,
        )

    raise STTConfigurationError("The configured STT provider is unavailable.")


def build_qwen_audio_endpoint(workspace_id: str, region: str) -> str:
    """Build the owner-selected Alibaba Model Studio workspace endpoint."""
    if not re.fullmatch(r"[A-Za-z0-9-]+", workspace_id):
        raise STTConfigurationError("DASHSCOPE_WORKSPACE_ID is invalid.")
    if not re.fullmatch(r"[a-z0-9-]+", region):
        raise STTConfigurationError("DASHSCOPE_REGION is invalid.")
    return (
        f"https://{workspace_id}.{region}.maas.aliyuncs.com"
        "/api/v1/services/aigc/multimodal-generation/generation"
    )


def _audio_format(audio_path: Path) -> tuple[str, str]:
    suffix = audio_path.suffix.lower()
    if suffix == ".mp3":
        return "mp3", "audio/mpeg"
    if suffix == ".wav":
        return "wav", "audio/wav"
    raise STTError("The configured STT adapter supports only MP3 and WAV audio.")


def _required_environment(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise STTConfigurationError(f"{name} is required for the configured STT.")
    return value


def _positive_float_environment(name: str, *, default: float) -> float:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        value = float(raw_value)
    except ValueError as error:
        raise STTConfigurationError(f"{name} must be a positive number.") from error
    if value <= 0:
        raise STTConfigurationError(f"{name} must be a positive number.")
    return value


def _language_hints(raw_value: str) -> tuple[str, ...]:
    hints = tuple(hint.strip() for hint in raw_value.split(",") if hint.strip())
    if not hints or len(hints) > 4:
        raise STTConfigurationError("STT_LANGUAGE_HINTS must contain 1 to 4 values.")
    return hints
