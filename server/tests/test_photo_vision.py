import logging
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import server.app.photo.gateway as gateway_module
from server.app.photo.domain import (
    InvalidPhotoLearningResultError,
    PhotoLearningResult,
    RelatedWord,
    UNSUITABLE_MESSAGE_ZH,
    validate_learning_result,
)
from server.app.photo.gateway import FakeVision, VisionConfigurationError, VisionError, create_vision_gateway
from server.app.photo.qwen import ProviderPhotoResult, QwenVision
from server.app.photo.service import PhotoLearningService
from server.app.tutor.schemas import StudentProfile


VALID_RESULT = PhotoLearningResult(
    status="ok",
    primary_word_en="apple",
    primary_meaning_zh="苹果",
    simple_sentence_en="This is an apple.",
    simple_sentence_zh="这是一个苹果。",
    practice_phrase="red apple",
    related_words=(RelatedWord("red", "红色"), RelatedWord("fruit", "水果")),
    question_en="What color is the apple?",
    encouragement_zh="很好！继续读吧。",
)


class MockParser:
    def __init__(self, parsed) -> None:
        self.parsed = parsed
        self.request = None

    async def parse(self, **request):
        self.request = request
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(parsed=self.parsed))]
        )


def mock_client(parser: MockParser):
    return SimpleNamespace(
        beta=SimpleNamespace(chat=SimpleNamespace(completions=parser))
    )


@pytest.mark.asyncio
async def test_fake_vision_is_deterministic_and_offline(tmp_path: Path) -> None:
    path = tmp_path / "normalized.jpg"
    path.write_bytes(b"offline")
    result = await FakeVision().analyze(image_path=path, system_prompt="policy")
    assert result.status == "ok"
    assert result.primary_word_en == "apple"
    assert result == await FakeVision().analyze(image_path=path, system_prompt="other")


def test_fake_vision_is_forbidden_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(VisionConfigurationError, match="Fake providers"):
        create_vision_gateway("fake")


@pytest.mark.parametrize("missing", ["DASHSCOPE_API_KEY", "DASHSCOPE_WORKSPACE_ID"])
def test_qwen_missing_config_is_normalized(monkeypatch: pytest.MonkeyPatch, missing: str) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setenv("DASHSCOPE_WORKSPACE_ID", "workspace-123")
    monkeypatch.delenv(missing)
    with pytest.raises(VisionConfigurationError, match=missing):
        create_vision_gateway("qwen")


def test_qwen_factory_reuses_beijing_workspace_and_hides_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}
    client = mock_client(MockParser(None))
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setenv("DASHSCOPE_WORKSPACE_ID", "workspace-123")
    monkeypatch.setenv("DASHSCOPE_REGION", "cn-beijing")
    monkeypatch.setenv("VISION_MODEL", "qwen3.7-flash")
    monkeypatch.setenv("VISION_TIMEOUT", "60")

    def fake_async_openai(**configuration):
        captured.update(configuration)
        return client

    monkeypatch.setattr(gateway_module, "AsyncOpenAI", fake_async_openai)
    gateway = create_vision_gateway("qwen")
    assert isinstance(gateway, QwenVision)
    assert gateway.model == "qwen3.7-flash"
    assert captured == {
        "api_key": "test-key",
        "base_url": "https://workspace-123.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
        "timeout": 60.0,
    }
    assert "test-key" not in repr(gateway)


@pytest.mark.asyncio
async def test_qwen_uses_base64_image_and_strict_pydantic_parse(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    parsed = ProviderPhotoResult(
        status="ok",
        primary_word_en="apple",
        primary_meaning_zh="苹果",
        simple_sentence_en="This is an apple.",
        simple_sentence_zh="这是一个苹果。",
        practice_phrase="apple",
        related_words=[],
        question_en="What is this?",
        encouragement_zh="读得很好！",
        message_zh=None,
    )
    parser = MockParser(parsed)
    path = tmp_path / "private-normalized.jpg"
    path.write_bytes(b"jpeg bytes")
    result = await QwenVision("qwen3.7-flash", mock_client(parser)).analyze(
        image_path=path,
        system_prompt="child privacy policy",
    )
    request = parser.request
    assert result.primary_word_en == "apple"
    assert request["model"] == "qwen3.7-flash"
    assert request["response_format"] is ProviderPhotoResult
    image_url = request["messages"][1]["content"][0]["image_url"]["url"]
    assert image_url.startswith("data:image/jpeg;base64,")
    assert str(path) not in repr(request["messages"])
    assert "base64" not in caplog.text
    schema = ProviderPhotoResult.model_json_schema()
    assert schema["additionalProperties"] is False


@pytest.mark.asyncio
async def test_qwen_malformed_parsed_result_is_normalized(tmp_path: Path) -> None:
    path = tmp_path / "photo.jpg"
    path.write_bytes(b"jpeg")
    with pytest.raises(VisionError, match="invalid response"):
        await QwenVision("qwen3.7-flash", mock_client(MockParser({"raw": "secret"}))).analyze(
            image_path=path,
            system_prompt="policy",
        )


@pytest.mark.asyncio
async def test_service_normalizes_structurally_invalid_provider_lesson(tmp_path: Path) -> None:
    class InvalidGateway:
        async def analyze(self, *, image_path, system_prompt):
            return PhotoLearningResult(status="ok", primary_word_en="apple")

    with pytest.raises(VisionError, match="invalid lesson"):
        await PhotoLearningService(InvalidGateway()).analyze(
            image_path=tmp_path / "normalized.jpg",
            student=StudentProfile(age=8, grade=3, english_level="beginner"),
        )


def test_learning_result_guard_accepts_all_public_statuses() -> None:
    assert validate_learning_result(VALID_RESULT) == VALID_RESULT
    assert validate_learning_result(PhotoLearningResult(status="unclear")).status == "unclear"
    assert validate_learning_result(PhotoLearningResult(status="unsuitable")).status == "unsuitable"


@pytest.mark.parametrize(
    "result",
    [
        replace(VALID_RESULT, practice_phrase=""),
        replace(VALID_RESULT, related_words=tuple(RelatedWord(f"word{i}", "词") for i in range(5))),
        replace(VALID_RESULT, related_words=(RelatedWord("apple", "苹果"),)),
        replace(VALID_RESULT, practice_phrase="one two three four five six seven eight nine"),
        replace(VALID_RESULT, practice_phrase="中文"),
    ],
)
def test_learning_result_guard_rejects_invalid_structure(result: PhotoLearningResult) -> None:
    with pytest.raises(InvalidPhotoLearningResultError):
        validate_learning_result(result)


@pytest.mark.parametrize(
    "sensitive_value",
    ["https://private.example", "child@example.com", "Call 138 0013 8000"],
)
def test_sensitive_looking_result_becomes_safe_unsuitable(sensitive_value: str) -> None:
    result = replace(VALID_RESULT, primary_meaning_zh=sensitive_value)
    guarded = validate_learning_result(result)
    assert guarded == PhotoLearningResult(
        status="unsuitable", message_zh=UNSUITABLE_MESSAGE_ZH
    )
