"""Thin student profile repository boundary."""

from typing import Protocol, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.student_profile.model import StudentProfileRecord
from server.app.tutor.schemas import EnglishLevel, StudentProfile


class StudentProfileRepository(Protocol):
    async def get(self, client_id: str) -> StudentProfile | None: ...

    async def save(self, client_id: str, profile: StudentProfile) -> StudentProfile: ...


class SQLAlchemyStudentProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, client_id: str) -> StudentProfile | None:
        record = await self._find(client_id)
        return _to_domain(record) if record is not None else None

    async def save(self, client_id: str, profile: StudentProfile) -> StudentProfile:
        record = await self._find(client_id)
        if record is None:
            record = StudentProfileRecord(client_id=client_id)
            self._session.add(record)

        record.age = profile.age
        record.grade = profile.grade
        record.english_level = profile.english_level
        await self._session.commit()
        await self._session.refresh(record)
        return _to_domain(record)

    async def _find(self, client_id: str) -> StudentProfileRecord | None:
        result = await self._session.execute(
            select(StudentProfileRecord).where(StudentProfileRecord.client_id == client_id)
        )
        return result.scalar_one_or_none()


def _to_domain(record: StudentProfileRecord) -> StudentProfile:
    return StudentProfile(
        age=record.age,
        grade=record.grade,
        english_level=cast(EnglishLevel, record.english_level),
    )
