"""Vision provider boundary and configured gateway factory."""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Protocol

from openai import AsyncOpenAI

from server.app.provider_environment import ProviderEnvironmentError, ensure_fake_provider_allowed
from server.app.tutor.llm import build_qwen_llm_base_url
from server.app.photo.domain import PhotoLearningResult, RelatedWord


class VisionError(RuntimeError):
    """Normalized Vision provider failure."""


class VisionConfigurationError(VisionError):
    """Raised when the configured Vision provider is unavailable."""


class VisionGateway(Protocol):
    async def analyze(self, *, image_path: Path, system_prompt: str) -> PhotoLearningResult: ...


@dataclass(slots=True)
class FakeVision:
    """Deterministic, fully offline Photo English provider."""

    async def analyze(self, *, image_path: Path, system_prompt: str) -> PhotoLearningResult:
        return PhotoLearningResult(
            status="ok",
            primary_word_en="apple",
            primary_meaning_zh="苹果",
            simple_sentence_en="This is a red apple.",
            simple_sentence_zh="这是一个红苹果。",
            practice_phrase="apple",
            related_words=(
                RelatedWord(word_en="red", meaning_zh="红色"),
                RelatedWord(word_en="fruit", meaning_zh="水果"),
            ),
            question_en="What color is the apple?",
            encouragement_zh="很好！来读一读 apple 吧。",
        )


def create_vision_gateway(provider: str | None = None) -> VisionGateway:
    selected = provider if provider is not None else os.getenv("VISION_PROVIDER", "fake")
    try:
        ensure_fake_provider_allowed(selected)
    except ProviderEnvironmentError as error:
        raise VisionConfigurationError(str(error)) from error

    normalized = selected.strip().lower()
    if normalized in {"", "fake"}:
        return FakeVision()
    if normalized == "qwen":
        from server.app.photo.qwen import QwenVision

        api_key = _required("DASHSCOPE_API_KEY")
        workspace_id = _required("DASHSCOPE_WORKSPACE_ID")
        region = os.getenv("DASHSCOPE_REGION", "cn-beijing").strip()
        model = os.getenv("VISION_MODEL", "qwen3.7-flash").strip()
        if not model:
            raise VisionConfigurationError("VISION_MODEL is required for Qwen Vision.")
        timeout = _positive_timeout()
        try:
            base_url = build_qwen_llm_base_url(workspace_id, region)
        except Exception as error:
            raise VisionConfigurationError("Qwen Vision endpoint configuration is invalid.") from error
        return QwenVision(
            model=model,
            client=AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout),
        )
    raise VisionConfigurationError("The configured Vision provider is unavailable.")


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise VisionConfigurationError(f"{name} is required for Qwen Vision.")
    return value


def _positive_timeout() -> float:
    raw = os.getenv("VISION_TIMEOUT", "60").strip()
    try:
        timeout = float(raw)
    except ValueError as error:
        raise VisionConfigurationError("VISION_TIMEOUT must be a positive number.") from error
    if timeout <= 0:
        raise VisionConfigurationError("VISION_TIMEOUT must be a positive number.")
    return timeout
