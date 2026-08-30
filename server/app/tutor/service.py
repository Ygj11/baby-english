"""Tutor text-chat orchestration."""

from dataclasses import dataclass

from server.app.tutor.llm import LLMGateway
from server.app.tutor.prompt_builder import build_system_prompt
from server.app.tutor.schemas import StudentProfile


@dataclass(slots=True)
class TutorService:
    llm: LLMGateway

    async def reply(self, message: str, student: StudentProfile) -> str:
        """Generate one reply without persistence or streaming."""
        return await self.llm.generate(
            system_prompt=build_system_prompt(student),
            message=message,
        )
