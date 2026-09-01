"""Explicit LlamaIndex embedding configuration for textbook RAG."""

from dataclasses import dataclass, field
import os
from typing import Any

from llama_index.core.embeddings import MockEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding

from server.app.provider_environment import ProviderEnvironmentError, ensure_fake_provider_allowed
from server.app.textbook.domain import TextbookConfigurationError
from server.app.tutor.llm import LLMConfigurationError, build_qwen_llm_base_url


DEFAULT_EMBEDDING_MODEL = "qwen3.7-text-embedding"
DEFAULT_EMBEDDING_DIMENSIONS = 1024


class SafeOpenAIEmbedding(OpenAIEmbedding):
    """OpenAI-compatible embedding integration with a secret-free repr."""

    def __repr__(self) -> str:
        return (
            f"SafeOpenAIEmbedding(model_name={self.model_name!r}, "
            f"embed_batch_size={self.embed_batch_size}, dimensions={self.dimensions})"
        )

    def __str__(self) -> str:
        return repr(self)


@dataclass(frozen=True, slots=True)
class ConfiguredTextbookEmbedding:
    provider: str
    model_name: str
    dimensions: int
    embed_model: Any = field(repr=False)


def create_textbook_embedding(provider: str | None = None) -> ConfiguredTextbookEmbedding:
    selected = (provider if provider is not None else os.getenv("EMBEDDING_PROVIDER", "fake")).strip().lower()
    try:
        ensure_fake_provider_allowed(selected)
    except ProviderEnvironmentError as error:
        raise TextbookConfigurationError(str(error)) from error

    dimensions = _bounded_integer_environment(
        "EMBEDDING_DIMENSIONS", default=DEFAULT_EMBEDDING_DIMENSIONS, minimum=1, maximum=4096
    )
    if selected in {"", "fake"}:
        return ConfiguredTextbookEmbedding(
            provider="fake",
            model_name="fake-textbook-embedding",
            dimensions=dimensions,
            embed_model=MockEmbedding(embed_dim=dimensions, model_name="fake-textbook-embedding"),
        )
    if selected != "qwen":
        raise TextbookConfigurationError("The configured embedding provider is unavailable.")

    model = os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL).strip()
    if model != DEFAULT_EMBEDDING_MODEL:
        raise TextbookConfigurationError("The configured Qwen embedding model is unsupported.")
    if dimensions != DEFAULT_EMBEDDING_DIMENSIONS:
        raise TextbookConfigurationError("Qwen textbook embeddings must use 1024 dimensions.")
    api_key = _required_environment("DASHSCOPE_API_KEY")
    workspace_id = _required_environment("DASHSCOPE_WORKSPACE_ID")
    region = os.getenv("DASHSCOPE_REGION", "cn-beijing").strip()
    if region != "cn-beijing":
        raise TextbookConfigurationError("Textbook embeddings require the Beijing Workspace.")
    timeout = _positive_float_environment("EMBEDDING_TIMEOUT", default=60.0)
    try:
        base_url = build_qwen_llm_base_url(workspace_id, region)
    except LLMConfigurationError as error:
        raise TextbookConfigurationError(str(error)) from error
    return ConfiguredTextbookEmbedding(
        provider="qwen",
        model_name=model,
        dimensions=dimensions,
        embed_model=SafeOpenAIEmbedding(
            model_name=model,
            api_key=api_key,
            api_base=base_url,
            dimensions=dimensions,
            embed_batch_size=20,
            timeout=timeout,
        ),
    )


def _required_environment(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise TextbookConfigurationError(f"{name} is required for Qwen embeddings.")
    return value


def _positive_float_environment(name: str, *, default: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = float(raw)
    except ValueError as error:
        raise TextbookConfigurationError(f"{name} must be a positive number.") from error
    if value <= 0:
        raise TextbookConfigurationError(f"{name} must be a positive number.")
    return value


def _bounded_integer_environment(name: str, *, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as error:
        raise TextbookConfigurationError(f"{name} must be an integer.") from error
    if not minimum <= value <= maximum:
        raise TextbookConfigurationError(f"{name} is outside the supported range.")
    return value
