import os

import pytest

from server.app.textbook.embedding import create_textbook_embedding


@pytest.mark.real_provider
@pytest.mark.asyncio
async def test_qwen_textbook_embedding_real_provider_returns_1024_dimensions() -> None:
    if os.getenv("RUN_REAL_PROVIDER_TESTS") != "1":
        pytest.skip("Set RUN_REAL_PROVIDER_TESTS=1 for real provider integration.")
    if not os.getenv("DASHSCOPE_API_KEY") or not os.getenv("DASHSCOPE_WORKSPACE_ID"):
        pytest.skip("DASHSCOPE_API_KEY and DASHSCOPE_WORKSPACE_ID are required.")

    embedding = create_textbook_embedding("qwen")
    vectors = await embedding.embed_model.aget_text_embedding_batch(
        ["A small blue toy bear.", "A yellow bird sings."], show_progress=False
    )
    assert embedding.model_name == "qwen3.7-text-embedding"
    assert embedding.dimensions == 1024
    assert len(vectors) == 2
    assert all(len(vector) == 1024 for vector in vectors)
