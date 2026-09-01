"""Scenario role-play application orchestration."""

from dataclasses import dataclass
from collections.abc import Callable

from server.app.scenario.assessment import SceneGoalAssessor
from server.app.scenario.catalog import get_scene
from server.app.scenario.domain import (
    SceneDefinition,
    ScenarioCompletion,
    ScenarioMessage,
    ScenarioSession,
)
from server.app.scenario.prompt import build_scene_prompt
from server.app.scenario.repository import SQLAlchemyScenarioRepository
from server.app.tutor.llm import LLMError, LLMGateway, LLMMessage
from server.app.tutor.schemas import StudentProfile


class UnknownSceneError(LookupError):
    pass


@dataclass(frozen=True, slots=True)
class PreparedTurn:
    session_id: int
    message: str
    reply: str


@dataclass(slots=True)
class ScenarioService:
    repository: SQLAlchemyScenarioRepository

    def scene(self, scene_id: str) -> SceneDefinition:
        scene = get_scene(scene_id)
        if scene is None:
            raise UnknownSceneError
        return scene

    async def prepare_turn(
        self,
        *,
        client_id: str,
        session_id: int,
        student: StudentProfile,
        message: str,
        llm: LLMGateway,
    ) -> PreparedTurn:
        session = await self.repository.get(client_id, session_id)
        await self.repository.require_turn_capacity(session)
        scene = self.scene(session.scene_id)
        progress = await self.repository.progress(client_id, scene)
        history = tuple(
            LLMMessage(role=turn.role, content=turn.content) for turn in session.turns
        )
        reply = await llm.generate(
            system_prompt=build_scene_prompt(
                student, scene, progress.completed_goal_ids
            ),
            history=history,
            message=message,
        )
        reply = reply.strip()
        if not reply or len(reply) > 1000:
            raise LLMError("The scenario LLM returned an invalid reply.")
        return PreparedTurn(session_id, message, reply)

    async def save_turn(
        self, client_id: str, prepared: PreparedTurn
    ) -> ScenarioSession:
        return await self.repository.append_pair(
            client_id,
            prepared.session_id,
            prepared.message,
            prepared.reply,
        )

    async def complete(
        self,
        *,
        client_id: str,
        session_id: int,
        assessor_factory: Callable[[], SceneGoalAssessor],
    ) -> ScenarioCompletion:
        session = await self.repository.get(client_id, session_id)
        scene = self.scene(session.scene_id)
        if session.status == "completed":
            return await self.repository.completed_result(client_id, scene, session)
        if not any(turn.role == "user" for turn in session.turns):
            from server.app.scenario.repository import ScenarioCompletionRequiresLearnerError

            raise ScenarioCompletionRequiresLearnerError
        assessor = assessor_factory()
        assessment = await assessor.assess(scene, session.turns)
        return await self.repository.complete_atomic(
            client_id, scene, session_id, assessment
        )
