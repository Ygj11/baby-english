"""Pronunciation provider gateway and factory."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from server.app.pronunciation.domain import (
    EvaluationCategory,
    PronunciationResult,
    WordPronunciationScore,
)
from server.app.provider_environment import (
    ProviderEnvironmentError,
    ensure_fake_provider_allowed,
)


class PronunciationError(RuntimeError):
    """Normalized pronunciation provider request failure."""


class PronunciationConfigurationError(PronunciationError):
    """Raised when the selected pronunciation provider is misconfigured."""


class PronunciationGateway(Protocol):
    async def evaluate(
        self,
        *,
        reference_text: str,
        audio_path: Path,
        category: EvaluationCategory,
    ) -> PronunciationResult: ...


@dataclass(frozen=True, slots=True)
class FakePronunciationGateway:
    """Deterministic offline pronunciation provider."""

    async def evaluate(
        self,
        *,
        reference_text: str,
        audio_path: Path,
        category: EvaluationCategory,
    ) -> PronunciationResult:
        return PronunciationResult(
            overall_score=88.0,
            accuracy_score=86.0,
            fluency_score=90.0,
            completeness_score=100.0,
            standard_score=84.0,
            rejected=False,
            words=(WordPronunciationScore(word=reference_text, score=86.0),),
        )


def create_pronunciation_gateway(
    provider: str | None = None,
) -> PronunciationGateway:
    selected = provider if provider is not None else os.getenv("ISE_PROVIDER", "")
    try:
        ensure_fake_provider_allowed(selected)
    except ProviderEnvironmentError as error:
        raise PronunciationConfigurationError(str(error)) from error

    normalized = selected.strip().lower()
    if normalized in {"", "fake"}:
        return FakePronunciationGateway()
    if normalized == "xunfei":
        from server.app.pronunciation.xunfei import XunfeiISEConfig, XunfeiISEPronunciationGateway

        return XunfeiISEPronunciationGateway(
            XunfeiISEConfig(
                app_id=_required_environment("XFYUN_APP_ID"),
                api_key=_required_environment("XFYUN_API_KEY"),
                api_secret=_required_environment("XFYUN_API_SECRET"),
                timeout=_positive_timeout(),
            )
        )
    raise PronunciationConfigurationError(
        "The configured pronunciation provider is unavailable."
    )


def _required_environment(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise PronunciationConfigurationError(
            f"{name} is required for the configured pronunciation provider."
        )
    return value


def _positive_timeout() -> float:
    raw_value = os.getenv("ISE_TIMEOUT", "60").strip()
    try:
        timeout = float(raw_value)
    except ValueError as error:
        raise PronunciationConfigurationError("ISE_TIMEOUT must be positive.") from error
    if timeout <= 0:
        raise PronunciationConfigurationError("ISE_TIMEOUT must be positive.")
    return timeout
