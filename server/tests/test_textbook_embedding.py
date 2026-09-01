import pytest

from server.app.textbook.domain import TextbookConfigurationError
from server.app.textbook.embedding import create_textbook_embedding


def test_fake_embedding_is_offline_and_forbidden_in_production(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    fake = create_textbook_embedding("fake")
    assert fake.provider == "fake"
    assert fake.dimensions == 1024
    assert len(fake.embed_model.get_text_embedding("synthetic text")) == 1024

    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(TextbookConfigurationError, match="forbidden"):
        create_textbook_embedding("fake")


def test_qwen_embedding_reuses_beijing_workspace_with_bounded_batch(monkeypatch) -> None:
    secret = "dashscope-secret-must-not-escape"
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DASHSCOPE_API_KEY", secret)
    monkeypatch.setenv("DASHSCOPE_WORKSPACE_ID", "workspace-123")
    monkeypatch.setenv("DASHSCOPE_REGION", "cn-beijing")
    monkeypatch.setenv("EMBEDDING_MODEL", "qwen3.7-text-embedding")
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "1024")
    configured = create_textbook_embedding("qwen")
    assert configured.provider == "qwen"
    assert configured.model_name == "qwen3.7-text-embedding"
    assert configured.dimensions == 1024
    assert configured.embed_model.embed_batch_size <= 20
    assert "workspace-123.cn-beijing.maas.aliyuncs.com/compatible-mode/v1" in str(
        configured.embed_model.api_base
    )
    assert secret not in repr(configured)
    assert secret not in repr(configured.embed_model)
    assert secret not in str(configured.embed_model)


@pytest.mark.parametrize(
    ("missing", "match"),
    [("DASHSCOPE_API_KEY", "DASHSCOPE_API_KEY"), ("DASHSCOPE_WORKSPACE_ID", "DASHSCOPE_WORKSPACE_ID")],
)
def test_qwen_embedding_missing_configuration_is_normalized(monkeypatch, missing, match) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "key")
    monkeypatch.setenv("DASHSCOPE_WORKSPACE_ID", "workspace")
    monkeypatch.delenv(missing, raising=False)
    with pytest.raises(TextbookConfigurationError, match=match):
        create_textbook_embedding("qwen")


def test_qwen_embedding_rejects_wrong_model_dimensions_or_region(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "key")
    monkeypatch.setenv("DASHSCOPE_WORKSPACE_ID", "workspace")
    monkeypatch.setenv("DASHSCOPE_REGION", "cn-beijing")
    monkeypatch.setenv("EMBEDDING_MODEL", "wrong")
    with pytest.raises(TextbookConfigurationError, match="unsupported"):
        create_textbook_embedding("qwen")
    monkeypatch.setenv("EMBEDDING_MODEL", "qwen3.7-text-embedding")
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "768")
    with pytest.raises(TextbookConfigurationError, match="1024"):
        create_textbook_embedding("qwen")
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "1024")
    monkeypatch.setenv("DASHSCOPE_REGION", "ap-southeast-1")
    with pytest.raises(TextbookConfigurationError, match="Beijing"):
        create_textbook_embedding("qwen")
