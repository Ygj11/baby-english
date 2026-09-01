import os
from pathlib import Path

import pytest

from server.app.textbook.domain import Textbook
from server.app.textbook.embedding import create_textbook_embedding
from server.app.textbook.index import ingest_textbook_index
from server.app.textbook.retriever import TextbookRetriever
from server.app.textbook.service import TextbookQAService
from server.app.tutor.llm import create_llm
from server.app.tutor.schemas import StudentProfile
from server.tests.textbook_helpers import synthetic_source


@pytest.mark.real_provider
@pytest.mark.asyncio
async def test_textbook_rag_e2e_real_qwen_uses_synthetic_source(tmp_path: Path) -> None:
    if os.getenv("RUN_REAL_PROVIDER_TESTS") != "1":
        pytest.skip("Set RUN_REAL_PROVIDER_TESTS=1 for real provider integration.")
    if not os.getenv("DASHSCOPE_API_KEY") or not os.getenv("DASHSCOPE_WORKSPACE_ID"):
        pytest.skip("DASHSCOPE_API_KEY and DASHSCOPE_WORKSPACE_ID are required.")

    source = synthetic_source(tmp_path / "synthetic-source")
    embedding = create_textbook_embedding("qwen")
    result = ingest_textbook_index(source, embedding, index_root=tmp_path / "indexes")
    textbook = Textbook(
        id=1,
        slug=source.manifest.slug,
        publisher=source.manifest.publisher,
        series=source.manifest.series,
        grade=source.manifest.grade,
        semester=source.manifest.semester,
        title=source.manifest.title,
        version=source.manifest.version,
        source_sha256=source.source_sha256,
        embedding_model=embedding.model_name,
        embedding_dimensions=embedding.dimensions,
        index_schema_version=result.index_manifest.schema_version,
        indexed_at=result.indexed_at,
    )
    answer = await TextbookQAService(
        retriever=TextbookRetriever(embedding, index_root=tmp_path / "indexes", top_k=2),
        llm=create_llm("qwen"),
    ).answer(
        student=StudentProfile(age=8, grade=3, english_level="beginner"),
        textbook=textbook,
        current_unit_no=1,
        question="What color is Milo, and what animal is Milo?",
    )
    normalized = answer.answer.lower()
    assert answer.found is True
    assert answer.sources and answer.sources[0].unit_no == 1
    assert any(token in normalized for token in ("blue", "蓝"))
    assert any(token in normalized for token in ("bear", "熊"))
