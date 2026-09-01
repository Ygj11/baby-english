import json
from pathlib import Path

import pytest

from server.app.textbook.domain import Textbook, TextbookIndexError
from server.app.textbook.embedding import ConfiguredTextbookEmbedding, create_textbook_embedding
from server.app.textbook.index import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    INDEX_MANIFEST_FILE,
    assert_index_compatible,
    ingest_textbook_index,
    read_index_manifest,
)
from server.app.textbook.retriever import TextbookRetriever
from server.tests.textbook_helpers import synthetic_source


def fake_embedding(monkeypatch) -> ConfiguredTextbookEmbedding:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "1024")
    return create_textbook_embedding("fake")


def domain_book(source, result) -> Textbook:
    return Textbook(
        id=1,
        slug=source.manifest.slug,
        publisher=source.manifest.publisher,
        series=source.manifest.series,
        grade=source.manifest.grade,
        semester=source.manifest.semester,
        title=source.manifest.title,
        version=source.manifest.version,
        source_sha256=source.source_sha256,
        embedding_model=result.index_manifest.embedding_model,
        embedding_dimensions=result.index_manifest.embedding_dimensions,
        index_schema_version=result.index_manifest.schema_version,
        indexed_at=result.indexed_at,
    )


@pytest.mark.asyncio
async def test_ingestion_persists_reloads_metadata_and_filters_exact_unit(
    tmp_path: Path, monkeypatch
) -> None:
    source = synthetic_source(tmp_path / "source")
    embedding = fake_embedding(monkeypatch)
    root = tmp_path / "runtime-indexes"
    result = ingest_textbook_index(source, embedding, index_root=root)
    index_dir = root / source.manifest.slug
    assert result.rebuilt is True
    assert (index_dir / "docstore.json").is_file()
    manifest = read_index_manifest(index_dir)
    assert manifest.chunk_size == CHUNK_SIZE
    assert manifest.chunk_overlap == CHUNK_OVERLAP
    manifest_text = (index_dir / INDEX_MANIFEST_FILE).read_text(encoding="utf-8")
    assert source.source_sha256 in manifest_text
    assert "Milo is a small blue bear" not in manifest_text
    assert str(tmp_path / "source") not in manifest_text

    chunks = await TextbookRetriever(embedding, index_root=root, top_k=1).retrieve(
        domain_book(source, result), question="Which bird sings?", unit_no=2
    )
    assert len(chunks) == 1
    assert chunks[0].unit_no == 2
    assert chunks[0].unit_title == "Bird Songs"
    assert chunks[0].lesson == "Lesson 1"
    assert chunks[0].page == 12
    assert chunks[0].source_record == 2
    assert "Pip" in chunks[0].text
    assert not hasattr(chunks[0], "node_id")
    assert not hasattr(chunks[0], "source_path")


def test_identical_is_noop_changed_fingerprint_rebuilds_and_stale_fails(
    tmp_path: Path, monkeypatch
) -> None:
    embedding = fake_embedding(monkeypatch)
    root = tmp_path / "indexes"
    first_source = synthetic_source(tmp_path / "source-one")
    first = ingest_textbook_index(first_source, embedding, index_root=root)
    second = ingest_textbook_index(first_source, embedding, index_root=root)
    assert first.rebuilt is True
    assert second.rebuilt is False

    changed_source = synthetic_source(tmp_path / "source-two", changed=True)
    changed = ingest_textbook_index(changed_source, embedding, index_root=root)
    assert changed.rebuilt is True
    assert changed_source.source_sha256 != first_source.source_sha256
    assert read_index_manifest(root / first_source.manifest.slug).source_sha256 == changed_source.source_sha256

    incompatible = ConfiguredTextbookEmbedding(
        provider="fake",
        model_name="other-fake",
        dimensions=embedding.dimensions,
        embed_model=embedding.embed_model,
    )
    with pytest.raises(TextbookIndexError, match="stale or incompatible"):
        assert_index_compatible(
            read_index_manifest(root / first_source.manifest.slug),
            textbook_slug=changed_source.manifest.slug,
            source_sha256=changed_source.source_sha256,
            embedding=incompatible,
        )


def test_failed_rebuild_keeps_previous_index_and_cleans_temp(
    tmp_path: Path, monkeypatch
) -> None:
    embedding = fake_embedding(monkeypatch)
    root = tmp_path / "indexes"
    first_source = synthetic_source(tmp_path / "source-one")
    ingest_textbook_index(first_source, embedding, index_root=root)
    original_manifest = (root / first_source.manifest.slug / INDEX_MANIFEST_FILE).read_text()
    changed_source = synthetic_source(tmp_path / "source-two", changed=True)

    def fail_pipeline(*args, **kwargs):
        raise RuntimeError("synthetic embedding failure with secret")

    monkeypatch.setattr("server.app.textbook.index.IngestionPipeline.run", fail_pipeline)
    with pytest.raises(TextbookIndexError, match="could not be built safely"):
        ingest_textbook_index(changed_source, embedding, index_root=root)
    assert (root / first_source.manifest.slug / INDEX_MANIFEST_FILE).read_text() == original_manifest
    assert not [item for item in root.iterdir() if item.name.startswith(".synthetic-rag-book-")]


def test_top_k_is_bounded(tmp_path: Path, monkeypatch) -> None:
    embedding = fake_embedding(monkeypatch)
    with pytest.raises(Exception, match="between 1 and 10"):
        TextbookRetriever(embedding, index_root=tmp_path, top_k=11)
