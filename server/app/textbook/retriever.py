"""Provider-neutral retrieval over a persisted LlamaIndex index."""

import os
from pathlib import Path

from llama_index.core.schema import MetadataMode
from llama_index.core.vector_stores import FilterOperator, MetadataFilter, MetadataFilters

from server.app.textbook.domain import RetrievedTextbookChunk, Textbook, TextbookConfigurationError
from server.app.textbook.embedding import ConfiguredTextbookEmbedding
from server.app.textbook.index import (
    assert_index_compatible,
    load_persisted_index,
    read_index_manifest,
    textbook_index_root,
)


class TextbookRetriever:
    def __init__(
        self,
        embedding: ConfiguredTextbookEmbedding,
        *,
        index_root: Path | None = None,
        top_k: int | None = None,
    ) -> None:
        self._embedding = embedding
        self._index_root = (index_root or textbook_index_root()).resolve()
        self._top_k = top_k if top_k is not None else _retrieval_top_k()
        if not 1 <= self._top_k <= 10:
            raise TextbookConfigurationError("TEXTBOOK_RETRIEVAL_TOP_K must be between 1 and 10.")

    async def retrieve(
        self, textbook: Textbook, *, question: str, unit_no: int | None
    ) -> tuple[RetrievedTextbookChunk, ...]:
        index_dir = self._index_root / textbook.slug
        manifest = read_index_manifest(index_dir)
        assert_index_compatible(
            manifest,
            textbook_slug=textbook.slug,
            source_sha256=textbook.source_sha256,
            embedding=self._embedding,
        )
        index = load_persisted_index(index_dir, self._embedding)
        filters = None
        if unit_no is not None:
            filters = MetadataFilters(
                filters=[
                    MetadataFilter(
                        key="unit_no", value=unit_no, operator=FilterOperator.EQ
                    )
                ]
            )
        retriever = index.as_retriever(similarity_top_k=self._top_k, filters=filters)
        try:
            nodes = await retriever.aretrieve(question)
        except Exception as error:
            raise TextbookIndexError("Textbook retrieval failed.") from error
        chunks: list[RetrievedTextbookChunk] = []
        for item in nodes:
            metadata = item.node.metadata
            chunks.append(
                RetrievedTextbookChunk(
                    text=item.node.get_content(metadata_mode=MetadataMode.NONE),
                    score=float(item.score) if item.score is not None else None,
                    unit_no=int(metadata["unit_no"]),
                    unit_title=str(metadata["unit_title"]),
                    lesson=str(metadata["lesson"]) or None,
                    page=int(metadata["page"]) or None,
                    source_record=int(metadata["source_record"]),
                )
            )
        return tuple(chunks)


def _retrieval_top_k() -> int:
    raw = os.getenv("TEXTBOOK_RETRIEVAL_TOP_K", "4").strip()
    try:
        return int(raw)
    except ValueError as error:
        raise TextbookConfigurationError("TEXTBOOK_RETRIEVAL_TOP_K must be an integer.") from error
