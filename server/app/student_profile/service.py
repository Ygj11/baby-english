"""Student profile application service."""

from dataclasses import dataclass

from server.app.student_profile.repository import StudentProfileRepository
from server.app.tutor.schemas import StudentProfile


@dataclass(slots=True)
class StudentProfileService:
    repository: StudentProfileRepository

    async def get(self, client_id: str) -> StudentProfile | None:
        return await self.repository.get(client_id)

    async def save(self, client_id: str, profile: StudentProfile) -> StudentProfile:
        return await self.repository.save(client_id, profile)
