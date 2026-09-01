from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from server.app.persistence.database import SessionFactory
from server.app.textbook.model import TextbookRecord, TextbookUnitRecord
from server.app.textbook.repository import (
    SQLAlchemyStudentTextbookRepository,
    SQLAlchemyTextbookRepository,
)
from server.tests.textbook_helpers import synthetic_source


async def add_book(tmp_path: Path, slug: str):
    source = synthetic_source(tmp_path / slug, slug=slug)
    async with SessionFactory() as session:
        return await SQLAlchemyTextbookRepository(session).upsert_ingested(
            source,
            embedding_model="fake-textbook-embedding",
            embedding_dimensions=1024,
            index_schema_version=1,
            indexed_at=datetime.now(UTC),
        )


@pytest.mark.asyncio
async def test_ingestion_metadata_and_idempotent_unique_slug(tmp_path: Path) -> None:
    slug = f"repo-{uuid4().hex}"
    source = synthetic_source(tmp_path / "one", slug=slug)
    async with SessionFactory() as session:
        repository = SQLAlchemyTextbookRepository(session)
        first = await repository.upsert_ingested(
            source,
            embedding_model="fake-textbook-embedding",
            embedding_dimensions=1024,
            index_schema_version=1,
            indexed_at=datetime.now(UTC),
        )
        second = await repository.upsert_ingested(
            source,
            embedding_model="fake-textbook-embedding",
            embedding_dimensions=1024,
            index_schema_version=1,
            indexed_at=datetime.now(UTC),
        )
        units = await repository.list_units(first.id)
    assert first.id == second.id
    assert [(unit.unit_no, unit.title) for unit in units] == [
        (1, "Toy Friends"),
        (2, "Bird Songs"),
    ]
    assert not set(TextbookRecord.__table__.columns.keys()).intersection(
        {"body", "text", "chunks", "embedding", "vector", "index_path", "source_path"}
    )


@pytest.mark.asyncio
async def test_database_enforces_unique_slug_and_book_unit(tmp_path: Path) -> None:
    book = await add_book(tmp_path, f"constraints-{uuid4().hex}")
    async with SessionFactory() as session:
        source = synthetic_source(tmp_path / "duplicate-source", slug=book.slug)
        session.add(
            TextbookRecord(
                slug=source.manifest.slug,
                publisher="Other",
                series="Other",
                grade=3,
                semester=1,
                title="Other",
                version="1",
                source_sha256="b" * 64,
                embedding_model="fake",
                embedding_dimensions=1024,
                index_schema_version=1,
                indexed_at=datetime.now(UTC),
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()
        session.add(TextbookUnitRecord(textbook_id=book.id, unit_no=1, title="Duplicate"))
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.asyncio
async def test_student_selection_is_client_scoped_and_unit_must_belong(
    tmp_path: Path,
) -> None:
    first = await add_book(tmp_path, f"selection-a-{uuid4().hex}")
    second = await add_book(tmp_path, f"selection-b-{uuid4().hex}")
    client_a = f"client_a_{uuid4().hex}"
    client_b = f"client_b_{uuid4().hex}"
    async with SessionFactory() as session:
        repository = SQLAlchemyStudentTextbookRepository(session)
        assert await repository.select(client_a, first.id, 1) is not None
        assert await repository.select(client_b, second.id, 2) is not None
        assert await repository.select(client_a, first.id, 999) is None
        current_a = await repository.get_current(client_a)
        current_b = await repository.get_current(client_b)
    assert current_a is not None and current_a.textbook.id == first.id
    assert current_a.current_unit_no == 1
    assert current_b is not None and current_b.textbook.id == second.id
    assert current_b.current_unit_no == 2


@pytest.mark.asyncio
async def test_reingestion_clears_a_selected_unit_that_no_longer_exists(tmp_path: Path) -> None:
    slug = f"reingest-{uuid4().hex}"
    source = synthetic_source(tmp_path / "source", slug=slug)
    async with SessionFactory() as session:
        books = SQLAlchemyTextbookRepository(session)
        book = await books.upsert_ingested(
            source,
            embedding_model="fake-textbook-embedding",
            embedding_dimensions=1024,
            index_schema_version=1,
            indexed_at=datetime.now(UTC),
        )
        selections = SQLAlchemyStudentTextbookRepository(session)
        client_id = f"reingest_client_{uuid4().hex}"
        assert await selections.select(client_id, book.id, 1) is not None
        without_unit_one = replace(
            source,
            records=(source.records[1],),
            source_sha256="c" * 64,
        )
        await books.upsert_ingested(
            without_unit_one,
            embedding_model="fake-textbook-embedding",
            embedding_dimensions=1024,
            index_schema_version=1,
            indexed_at=datetime.now(UTC),
        )
        current = await selections.get_current(client_id)
    assert current is not None and current.current_unit_no is None
