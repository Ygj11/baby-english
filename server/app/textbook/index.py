"""Build, validate, persist, and atomically replace local textbook indexes."""

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any

from llama_index.core import Document, StorageContext, VectorStoreIndex, load_index_from_storage
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import SentenceSplitter

from server.app.textbook.domain import TextbookIndexError, TextbookSource
from server.app.textbook.embedding import ConfiguredTextbookEmbedding


INDEX_SCHEMA_VERSION = 1
INDEX_MANIFEST_FILE = "baby_english_index_manifest.json"
CHUNK_SIZE = 384
CHUNK_OVERLAP = 48


@dataclass(frozen=True, slots=True)
class TextbookIndexManifest:
    schema_version: int
    textbook_slug: str
    source_sha256: str
    embedding_model: str
    embedding_dimensions: int
    chunk_size: int
    chunk_overlap: int


@dataclass(frozen=True, slots=True)
class TextbookIngestionResult:
    rebuilt: bool
    index_manifest: TextbookIndexManifest
    indexed_at: datetime


def textbook_index_root() -> Path:
    return Path(os.getenv("TEXTBOOK_INDEX_DIR", ".data/textbook_indexes")).expanduser().resolve()


def expected_index_manifest(
    source: TextbookSource, embedding: ConfiguredTextbookEmbedding
) -> TextbookIndexManifest:
    return TextbookIndexManifest(
        schema_version=INDEX_SCHEMA_VERSION,
        textbook_slug=source.manifest.slug,
        source_sha256=source.source_sha256,
        embedding_model=embedding.model_name,
        embedding_dimensions=embedding.dimensions,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )


def ingest_textbook_index(
    source: TextbookSource,
    embedding: ConfiguredTextbookEmbedding,
    *,
    index_root: Path | None = None,
) -> TextbookIngestionResult:
    root = (index_root or textbook_index_root()).resolve()
    root.mkdir(parents=True, exist_ok=True)
    target = root / source.manifest.slug
    expected = expected_index_manifest(source, embedding)
    current = read_index_manifest(target, required=False)
    if current == expected:
        _load_index(target, embedding)
        return TextbookIngestionResult(
            rebuilt=False,
            index_manifest=expected,
            indexed_at=datetime.now(UTC),
        )

    temp_path = Path(tempfile.mkdtemp(prefix=f".{source.manifest.slug}-", dir=root))
    backup_path = root / f".{source.manifest.slug}.previous"
    moved_previous = False
    try:
        documents = [
            Document(
                text=record.text,
                metadata={
                    "textbook_slug": source.manifest.slug,
                    "grade": source.manifest.grade,
                    "semester": source.manifest.semester,
                    "unit_no": record.unit_no,
                    "unit_title": record.unit_title,
                    "lesson": record.lesson or "",
                    "page": record.page if record.page is not None else 0,
                    "source_record": record.source_record,
                },
                excluded_embed_metadata_keys=[
                    "textbook_slug",
                    "grade",
                    "semester",
                    "unit_no",
                    "unit_title",
                    "lesson",
                    "page",
                    "source_record",
                ],
                excluded_llm_metadata_keys=[
                    "textbook_slug",
                    "grade",
                    "semester",
                    "unit_no",
                    "unit_title",
                    "lesson",
                    "page",
                    "source_record",
                ],
            )
            for record in source.records
        ]
        pipeline = IngestionPipeline(
            transformations=[
                SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP),
                embedding.embed_model,
            ]
        )
        nodes = pipeline.run(documents=documents)
        if not nodes:
            raise TextbookIndexError("Textbook ingestion produced no searchable chunks.")
        index = VectorStoreIndex(nodes, embed_model=embedding.embed_model, insert_batch_size=20)
        index.storage_context.persist(persist_dir=str(temp_path))
        _write_index_manifest(temp_path, expected)
        _load_index(temp_path, embedding)

        if backup_path.exists():
            shutil.rmtree(backup_path)
        if target.exists():
            target.rename(backup_path)
            moved_previous = True
        temp_path.rename(target)
        if moved_previous:
            shutil.rmtree(backup_path, ignore_errors=True)
    except TextbookIndexError:
        if moved_previous and not target.exists() and backup_path.exists():
            backup_path.rename(target)
        raise
    except Exception as error:
        if moved_previous and not target.exists() and backup_path.exists():
            backup_path.rename(target)
        raise TextbookIndexError("The textbook index could not be built safely.") from error
    finally:
        if temp_path.exists():
            shutil.rmtree(temp_path)

    return TextbookIngestionResult(
        rebuilt=True,
        index_manifest=expected,
        indexed_at=datetime.now(UTC),
    )


def read_index_manifest(
    index_dir: Path, *, required: bool = True
) -> TextbookIndexManifest | None:
    path = index_dir / INDEX_MANIFEST_FILE
    try:
        data: Any = json.loads(path.read_text(encoding="utf-8"))
        return TextbookIndexManifest(**data)
    except FileNotFoundError:
        if required:
            raise TextbookIndexError("The textbook index is unavailable.") from None
        return None
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
        if not required:
            return None
        raise TextbookIndexError("The textbook index manifest is invalid.") from None


def assert_index_compatible(
    manifest: TextbookIndexManifest,
    *,
    textbook_slug: str,
    source_sha256: str,
    embedding: ConfiguredTextbookEmbedding,
) -> None:
    expected = TextbookIndexManifest(
        schema_version=INDEX_SCHEMA_VERSION,
        textbook_slug=textbook_slug,
        source_sha256=source_sha256,
        embedding_model=embedding.model_name,
        embedding_dimensions=embedding.dimensions,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    if manifest != expected:
        raise TextbookIndexError("The textbook index is stale or incompatible.")


def load_persisted_index(index_dir: Path, embedding: ConfiguredTextbookEmbedding):
    return _load_index(index_dir, embedding)


def _load_index(index_dir: Path, embedding: ConfiguredTextbookEmbedding):
    try:
        storage = StorageContext.from_defaults(persist_dir=str(index_dir))
        return load_index_from_storage(storage, embed_model=embedding.embed_model)
    except Exception as error:
        raise TextbookIndexError("The textbook index could not be loaded.") from error


def _write_index_manifest(index_dir: Path, manifest: TextbookIndexManifest) -> None:
    (index_dir / INDEX_MANIFEST_FILE).write_text(
        json.dumps(asdict(manifest), ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
