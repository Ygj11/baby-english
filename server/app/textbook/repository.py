"""Focused repositories for textbook catalogue metadata and selection."""

from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.textbook.domain import StudentTextbookSelection, Textbook, TextbookSource, TextbookUnit
from server.app.textbook.model import StudentTextbookRecord, TextbookRecord, TextbookUnitRecord


class SQLAlchemyTextbookRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_ready(self) -> tuple[Textbook, ...]:
        result = await self._session.execute(select(TextbookRecord).order_by(TextbookRecord.grade, TextbookRecord.title))
        return tuple(_textbook(row) for row in result.scalars())

    async def get_ready(self, textbook_id: int) -> Textbook | None:
        result = await self._session.execute(select(TextbookRecord).where(TextbookRecord.id == textbook_id))
        row = result.scalar_one_or_none()
        return _textbook(row) if row is not None else None

    async def get_by_slug(self, slug: str) -> Textbook | None:
        result = await self._session.execute(select(TextbookRecord).where(TextbookRecord.slug == slug))
        row = result.scalar_one_or_none()
        return _textbook(row) if row is not None else None

    async def list_units(self, textbook_id: int) -> tuple[TextbookUnit, ...]:
        result = await self._session.execute(
            select(TextbookUnitRecord)
            .where(TextbookUnitRecord.textbook_id == textbook_id)
            .order_by(TextbookUnitRecord.unit_no)
        )
        return tuple(_unit(row) for row in result.scalars())

    async def upsert_ingested(
        self,
        source: TextbookSource,
        *,
        embedding_model: str,
        embedding_dimensions: int,
        index_schema_version: int,
        indexed_at: datetime,
    ) -> Textbook:
        result = await self._session.execute(
            select(TextbookRecord).where(TextbookRecord.slug == source.manifest.slug)
        )
        record = result.scalar_one_or_none()
        if record is None:
            record = TextbookRecord(slug=source.manifest.slug)
            self._session.add(record)
        manifest = source.manifest
        record.publisher = manifest.publisher
        record.series = manifest.series
        record.grade = manifest.grade
        record.semester = manifest.semester
        record.title = manifest.title
        record.version = manifest.version
        record.source_sha256 = source.source_sha256
        record.embedding_model = embedding_model
        record.embedding_dimensions = embedding_dimensions
        record.index_schema_version = index_schema_version
        record.indexed_at = indexed_at
        await self._session.flush()

        await self._session.execute(
            delete(TextbookUnitRecord).where(TextbookUnitRecord.textbook_id == record.id)
        )
        units = sorted({(item.unit_no, item.unit_title) for item in source.records})
        self._session.add_all(
            TextbookUnitRecord(textbook_id=record.id, unit_no=unit_no, title=title)
            for unit_no, title in units
        )
        valid_unit_numbers = [unit_no for unit_no, _title in units]
        await self._session.execute(
            update(StudentTextbookRecord)
            .where(
                StudentTextbookRecord.textbook_id == record.id,
                StudentTextbookRecord.current_unit_no.is_not(None),
                StudentTextbookRecord.current_unit_no.not_in(valid_unit_numbers),
            )
            .values(current_unit_no=None)
        )
        await self._session.commit()
        await self._session.refresh(record)
        return _textbook(record)


class SQLAlchemyStudentTextbookRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_current(self, client_id: str) -> StudentTextbookSelection | None:
        result = await self._session.execute(
            select(StudentTextbookRecord, TextbookRecord)
            .join(TextbookRecord, TextbookRecord.id == StudentTextbookRecord.textbook_id)
            .where(StudentTextbookRecord.client_id == client_id)
        )
        row = result.one_or_none()
        if row is None:
            return None
        selection, textbook = row
        return StudentTextbookSelection(
            textbook=_textbook(textbook), current_unit_no=selection.current_unit_no
        )

    async def select(
        self, client_id: str, textbook_id: int, current_unit_no: int | None
    ) -> StudentTextbookSelection | None:
        textbook_result = await self._session.execute(
            select(TextbookRecord).where(TextbookRecord.id == textbook_id)
        )
        textbook = textbook_result.scalar_one_or_none()
        if textbook is None:
            return None
        if current_unit_no is not None:
            unit_result = await self._session.execute(
                select(TextbookUnitRecord.id).where(
                    TextbookUnitRecord.textbook_id == textbook_id,
                    TextbookUnitRecord.unit_no == current_unit_no,
                )
            )
            if unit_result.scalar_one_or_none() is None:
                return None
        result = await self._session.execute(
            select(StudentTextbookRecord).where(StudentTextbookRecord.client_id == client_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            record = StudentTextbookRecord(client_id=client_id, textbook_id=textbook_id)
            self._session.add(record)
        record.textbook_id = textbook_id
        record.current_unit_no = current_unit_no
        await self._session.commit()
        return StudentTextbookSelection(
            textbook=_textbook(textbook), current_unit_no=current_unit_no
        )


def _textbook(record: TextbookRecord) -> Textbook:
    return Textbook(
        id=record.id,
        slug=record.slug,
        publisher=record.publisher,
        series=record.series,
        grade=record.grade,
        semester=record.semester,
        title=record.title,
        version=record.version,
        source_sha256=record.source_sha256,
        embedding_model=record.embedding_model,
        embedding_dimensions=record.embedding_dimensions,
        index_schema_version=record.index_schema_version,
        indexed_at=record.indexed_at,
    )


def _unit(record: TextbookUnitRecord) -> TextbookUnit:
    return TextbookUnit(
        id=record.id,
        textbook_id=record.textbook_id,
        unit_no=record.unit_no,
        title=record.title,
    )
