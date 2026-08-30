from types import SimpleNamespace

import httpx
import pytest
from openai import APITimeoutError

import server.app.tutor.llm as llm_module
from server.app.tutor.llm import (
    LLMConfigurationError,
    LLMError,
    QwenLLM,
    build_qwen_llm_base_url,
    create_llm,
)


class MockCompletions:
    def __init__(self, *, response=None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.request = None

    async def create(self, **request):
        self.request = request
        if self.error is not None:
            raise self.error
        return self.response


def mock_client(completions: MockCompletions):
    return SimpleNamespace(chat=SimpleNamespace(completions=completions))


def set_qwen_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("LLM_PROVIDER", "qwen")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setenv("DASHSCOPE_WORKSPACE_ID", "workspace-123")
    monkeypatch.setenv("DASHSCOPE_REGION", "cn-beijing")
    monkeypatch.setenv("LLM_MODEL", "qwen3.7-flash")
    monkeypatch.setenv("LLM_TIMEOUT", "60")


def test_qwen_beijing_base_url() -> None:
    assert build_qwen_llm_base_url("workspace-123", "cn-beijing") == (
        "https://workspace-123.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
    )


def test_factory_selects_qwen_and_maps_shared_dashscope_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_qwen_environment(monkeypatch)
    captured = {}
    client = mock_client(MockCompletions())

    def fake_async_openai(**configuration):
        captured.update(configuration)
        return client

    monkeypatch.setattr(llm_module, "AsyncOpenAI", fake_async_openai)

    llm = create_llm()

    assert isinstance(llm, QwenLLM)
    assert llm.model == "qwen3.7-flash"
    assert captured == {
        "api_key": "test-key",
        "base_url": (
            "https://workspace-123.cn-beijing.maas.aliyuncs.com"
            "/compatible-mode/v1"
        ),
        "timeout": 60.0,
    }
    assert "test-key" not in repr(llm)


@pytest.mark.asyncio
async def test_qwen_maps_child_tutor_system_and_user_messages() -> None:
    completions = MockCompletions(
        response=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Banana."))]
        )
    )
    llm = QwenLLM(model="qwen3.7-flash", client=mock_client(completions))

    reply = await llm.generate(
        system_prompt="Child tutor policy",
        message="香蕉英文怎么说？",
    )

    assert reply == "Banana."
    assert completions.request == {
        "model": "qwen3.7-flash",
        "messages": [
            {"role": "system", "content": "Child tutor policy"},
            {"role": "user", "content": "香蕉英文怎么说？"},
        ],
    }


@pytest.mark.asyncio
async def test_qwen_provider_error_is_normalized() -> None:
    completions = MockCompletions(
        error=APITimeoutError(
            request=httpx.Request("POST", "https://provider.test")
        )
    )
    llm = QwenLLM(model="qwen3.7-flash", client=mock_client(completions))

    with pytest.raises(LLMError, match="provider request failed"):
        await llm.generate(system_prompt="policy", message="hello")


@pytest.mark.parametrize(
    "missing_variable",
    ["DASHSCOPE_API_KEY", "DASHSCOPE_WORKSPACE_ID", "LLM_MODEL"],
)
def test_qwen_missing_configuration_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    missing_variable: str,
) -> None:
    set_qwen_environment(monkeypatch)
    monkeypatch.delenv(missing_variable)

    with pytest.raises(LLMConfigurationError, match=missing_variable):
        create_llm()
