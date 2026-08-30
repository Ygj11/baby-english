from types import SimpleNamespace

import httpx
import pytest
from openai import APITimeoutError, AuthenticationError

import server.app.tutor.llm as llm_module
from server.app.tutor.llm import (
    FakeLLM,
    LLMConfigurationError,
    LLMError,
    OpenAICompatibleLLM,
    create_llm,
)


class MockCompletions:
    def __init__(self, response=None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.request = None

    async def create(self, **request):
        self.request = request
        if self.error is not None:
            raise self.error
        return self.response


def mock_client(completions: MockCompletions):
    return SimpleNamespace(
        chat=SimpleNamespace(completions=completions),
    )


def set_real_llm_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("OPENAI_MODEL", "deepseek-v4-pro")
    monkeypatch.setenv("OPENAI_TIMEOUT", "1800")


def test_factory_selects_real_adapter_and_maps_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_real_llm_environment(monkeypatch)
    captured = {}
    client = mock_client(MockCompletions())

    def fake_async_openai(**configuration):
        captured.update(configuration)
        return client

    monkeypatch.setattr(llm_module, "AsyncOpenAI", fake_async_openai)

    llm = create_llm()

    assert isinstance(llm, OpenAICompatibleLLM)
    assert llm.model == "deepseek-v4-pro"
    assert captured == {
        "api_key": "test-key",
        "base_url": "https://api.deepseek.com",
        "timeout": 1800.0,
    }
    assert "test-key" not in repr(llm)


@pytest.mark.asyncio
async def test_messages_map_to_system_and_user_and_return_reply() -> None:
    completions = MockCompletions(
        response=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=" Apple. "))]
        )
    )
    llm = OpenAICompatibleLLM(
        model="deepseek-v4-pro",
        client=mock_client(completions),
    )

    reply = await llm.generate(
        system_prompt="Child tutor policy",
        message="苹果英文怎么说？",
    )

    assert reply == "Apple."
    assert completions.request == {
        "model": "deepseek-v4-pro",
        "messages": [
            {"role": "system", "content": "Child tutor policy"},
            {"role": "user", "content": "苹果英文怎么说？"},
        ],
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "provider_error",
    [
        APITimeoutError(request=httpx.Request("POST", "https://provider.test")),
        AuthenticationError(
            "invalid key",
            response=httpx.Response(
                401,
                request=httpx.Request("POST", "https://provider.test"),
            ),
            body=None,
        ),
    ],
)
async def test_provider_errors_are_normalized(provider_error: Exception) -> None:
    llm = OpenAICompatibleLLM(
        model="deepseek-v4-pro",
        client=mock_client(MockCompletions(error=provider_error)),
    )

    with pytest.raises(LLMError, match="provider request failed"):
        await llm.generate(system_prompt="policy", message="hello")


@pytest.mark.asyncio
@pytest.mark.parametrize("response", [SimpleNamespace(choices=[]), None])
async def test_invalid_provider_response_is_normalized(response) -> None:
    llm = OpenAICompatibleLLM(
        model="deepseek-v4-pro",
        client=mock_client(MockCompletions(response=response)),
    )

    with pytest.raises(LLMError, match="invalid response"):
        await llm.generate(system_prompt="policy", message="hello")


@pytest.mark.parametrize(
    "missing_variable",
    ["OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL"],
)
def test_missing_real_configuration_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    missing_variable: str,
) -> None:
    set_real_llm_environment(monkeypatch)
    monkeypatch.delenv(missing_variable)

    with pytest.raises(LLMConfigurationError, match=missing_variable):
        create_llm()


def test_fake_factory_still_works(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LLM_PROVIDER", "fake")

    assert isinstance(create_llm(), FakeLLM)
