from uuid import uuid4

import pytest
from sqlalchemy import func, select

from server.app.persistence.database import SessionFactory
from server.app.student_profile.model import StudentProfileRecord
from server.app.student_profile.repository import SQLAlchemyStudentProfileRepository
from server.app.tutor.schemas import StudentProfile


def client_id(label: str) -> str:
    return f"test_{label}_{uuid4().hex}"


@pytest.mark.asyncio
async def test_repository_create_get_upsert_update_and_isolation() -> None:
    owner_a = client_id("repo_a")
    owner_b = client_id("repo_b")
    initial = StudentProfile(age=8, grade=3, english_level="beginner")
    updated = StudentProfile(age=10, grade=5, english_level="elementary")

    async with SessionFactory() as session:
        repository = SQLAlchemyStudentProfileRepository(session)
        assert await repository.get(owner_a) is None

        assert await repository.save(owner_a, initial) == initial
        assert await repository.get(owner_a) == initial
        assert await repository.get(owner_b) is None

        assert await repository.save(owner_a, updated) == updated
        assert await repository.get(owner_a) == updated
        count = await session.scalar(
            select(func.count()).select_from(StudentProfileRecord).where(
                StudentProfileRecord.client_id == owner_a
            )
        )

    assert count == 1
