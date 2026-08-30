import pytest

from server.app.tutor.llm import (
    FakeLLM,
    LLMConfigurationError,
    create_llm,
)
from server.app.voice.stt import (
    FakeSTT,
    STTConfigurationError,
    create_stt,
)
from server.app.voice.tts import (
    FakeTTS,
    TTSConfigurationError,
    create_tts,
)

PROVIDERS = [
    ("LLM_PROVIDER", create_llm, FakeLLM, LLMConfigurationError),
    ("STT_PROVIDER", create_stt, FakeSTT, STTConfigurationError),
    ("TTS_PROVIDER", create_tts, FakeTTS, TTSConfigurationError),
]


@pytest.mark.parametrize(("variable", "factory", "fake_type", "error_type"), PROVIDERS)
def test_development_with_empty_provider_allows_fake(
    monkeypatch: pytest.MonkeyPatch,
    variable,
    factory,
    fake_type,
    error_type,
) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv(variable, raising=False)

    assert isinstance(factory(), fake_type)


@pytest.mark.parametrize(("variable", "factory", "fake_type", "error_type"), PROVIDERS)
def test_test_environment_with_fake_provider_allows_fake(
    monkeypatch: pytest.MonkeyPatch,
    variable,
    factory,
    fake_type,
    error_type,
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv(variable, "fake")

    assert isinstance(factory(), fake_type)


@pytest.mark.parametrize(("variable", "factory", "fake_type", "error_type"), PROVIDERS)
@pytest.mark.parametrize("provider", [None, "fake"])
def test_production_rejects_empty_and_fake_providers(
    monkeypatch: pytest.MonkeyPatch,
    variable,
    factory,
    fake_type,
    error_type,
    provider,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    if provider is None:
        monkeypatch.delenv(variable, raising=False)
    else:
        monkeypatch.setenv(variable, provider)

    with pytest.raises(error_type, match="Fake providers are forbidden"):
        factory()
