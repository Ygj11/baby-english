"""LLM adapter boundary for the tutor."""

import os
from dataclasses import dataclass, field
from typing import Any, Protocol

from openai import AsyncOpenAI, OpenAIError

from server.app.provider_environment import (
    ProviderEnvironmentError,
    ensure_fake_provider_allowed,
)


class LLMError(RuntimeError):
    """Normalized LLM failure raised by adapters."""


class LLMConfigurationError(LLMError):
    """Raised when the configured provider has no installed adapter."""


class LLMGateway(Protocol):
    async def generate(self, *, system_prompt: str, message: str) -> str:
        """Generate one tutor response."""


@dataclass(slots=True)
class FakeLLM:
    """Deterministic no-key LLM used by the local baseline and tests."""

    fixed_reply: str = "Apple 🍎. Repeat after me: apple."

    async def generate(self, *, system_prompt: str, message: str) -> str:
        return self.fixed_reply


@dataclass(slots=True)
class OpenAICompatibleLLM:
    """OpenAI-compatible chat adapter for the owner-selected DeepSeek API."""

    model: str
    client: Any = field(repr=False)

    async def generate(self, *, system_prompt: str, message: str) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                ],
            )
        except (OpenAIError, TimeoutError) as error:
            raise LLMError("The LLM provider request failed.") from error

        try:
            content = response.choices[0].message.content
        except (AttributeError, IndexError, TypeError) as error:
            raise LLMError("The LLM provider returned an invalid response.") from error

        if not isinstance(content, str) or not content.strip():
            raise LLMError("The LLM provider returned an empty response.")
        return content.strip()


def create_llm(provider: str | None = None) -> LLMGateway:
    """Create the configured LLM adapter without selecting a paid provider."""
    selected_provider = provider
    if selected_provider is None:
        selected_provider = os.getenv("LLM_PROVIDER", "")

    try:
        ensure_fake_provider_allowed(selected_provider)
    except ProviderEnvironmentError as error:
        raise LLMConfigurationError(str(error)) from error

    normalized_provider = selected_provider.strip().lower()
    if normalized_provider in {"", "fake"}:
        return FakeLLM()

    if normalized_provider == "openai_compatible":
        api_key = _required_environment("OPENAI_API_KEY")
        base_url = _required_environment("OPENAI_BASE_URL")
        model = _required_environment("OPENAI_MODEL")
        timeout = _positive_float_environment("OPENAI_TIMEOUT", default=1800.0)
        return OpenAICompatibleLLM(
            model=model,
            client=AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=timeout,
            ),
        )

    raise LLMConfigurationError("The configured LLM provider is unavailable.")


def _required_environment(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise LLMConfigurationError(f"{name} is required for the configured LLM.")
    return value


def _positive_float_environment(name: str, *, default: float) -> float:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        value = float(raw_value)
    except ValueError as error:
        raise LLMConfigurationError(f"{name} must be a positive number.") from error
    if value <= 0:
        raise LLMConfigurationError(f"{name} must be a positive number.")
    return value
