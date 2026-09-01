"""CLI entry point for safe external textbook ingestion."""

import argparse
import asyncio

from server.app.persistence.database import SessionFactory
from server.app.textbook.embedding import create_textbook_embedding
from server.app.textbook.index import ingest_textbook_index
from server.app.textbook.repository import SQLAlchemyTextbookRepository
from server.app.textbook.source import load_textbook_source


async def _persist_metadata(source, embedding, result) -> int:
    async with SessionFactory() as session:
        textbook = await SQLAlchemyTextbookRepository(session).upsert_ingested(
            source,
            embedding_model=embedding.model_name,
            embedding_dimensions=embedding.dimensions,
            index_schema_version=result.index_manifest.schema_version,
            indexed_at=result.indexed_at,
        )
    return textbook.id


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and index one external textbook package.")
    parser.add_argument("package_dir", help="Absolute path to the external textbook package")
    args = parser.parse_args()
    source = load_textbook_source(args.package_dir)
    embedding = create_textbook_embedding()
    result = ingest_textbook_index(source, embedding)
    textbook_id = asyncio.run(_persist_metadata(source, embedding, result))
    action = "rebuilt" if result.rebuilt else "unchanged"
    print(f"textbook ingestion ok: id={textbook_id} slug={source.manifest.slug} index={action}")


if __name__ == "__main__":
    main()
