"""Async persistence boundary for scenario memory and goal progress."""

import json
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.scenario.domain import (
    SceneAssessment,
    SceneDefinition,
    SceneProgress,
    ScenarioCompletion,
    ScenarioMessage,
    ScenarioSession,
)
from server.app.scenario.model import (
    ScenarioSessionRecord,
    ScenarioTurnRecord,
    SceneGoalProgressRecord,
)


MAX_PERSISTED_TURNS = 40


class ScenarioSessionNotFoundError(LookupError):
    pass


class ScenarioSessionInactiveError(RuntimeError):
    pass


class ScenarioTurnLimitError(RuntimeError):
    pass


class ScenarioCompletionRequiresLearnerError(ValueError):
    pass


class SQLAlchemyScenarioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def progress(self, client_id: str, scene: SceneDefinition) -> SceneProgress:
        rows = list(
            await self._session.scalars(
                select(SceneGoalProgressRecord).where(
                    SceneGoalProgressRecord.client_id == client_id,
                    SceneGoalProgressRecord.scene_id == scene.id,
                )
            )
        )
        found = {row.goal_id for row in rows}
        completed = tuple(goal.id for goal in scene.goals if goal.id in found)
        missing = tuple(goal.id for goal in scene.goals if goal.id not in found)
        return SceneProgress(completed, missing, len(completed), len(scene.goals))

    async def start(self, client_id: str, scene: SceneDefinition) -> ScenarioSession:
        stale_ids = list(
            await self._session.scalars(
                select(ScenarioSessionRecord.id).where(
                    ScenarioSessionRecord.client_id == client_id,
                    ScenarioSessionRecord.scene_id == scene.id,
                    ScenarioSessionRecord.status == "active",
                )
            )
        )
        if stale_ids:
            await self._session.execute(
                delete(ScenarioTurnRecord).where(ScenarioTurnRecord.session_id.in_(stale_ids))
            )
            await self._session.execute(
                delete(ScenarioSessionRecord).where(ScenarioSessionRecord.id.in_(stale_ids))
            )
        record = ScenarioSessionRecord(client_id=client_id, scene_id=scene.id, status="active")
        self._session.add(record)
        await self._session.flush()
        self._session.add(ScenarioTurnRecord(session_id=record.id, idx=0, role="assistant", content=scene.opening_line))
        await self._session.commit()
        return await self.get(client_id, record.id)

    async def get(self, client_id: str, session_id: int) -> ScenarioSession:
        record = await self._session.scalar(
            select(ScenarioSessionRecord).where(
                ScenarioSessionRecord.id == session_id,
                ScenarioSessionRecord.client_id == client_id,
            )
        )
        if record is None:
            raise ScenarioSessionNotFoundError
        turns = list(
            await self._session.scalars(
                select(ScenarioTurnRecord)
                .where(ScenarioTurnRecord.session_id == record.id)
                .order_by(ScenarioTurnRecord.idx)
            )
        )
        return ScenarioSession(
            id=record.id,
            client_id=record.client_id,
            scene_id=record.scene_id,
            status=record.status,  # type: ignore[arg-type]
            turns=tuple(ScenarioMessage(role=turn.role, content=turn.content) for turn in turns),  # type: ignore[arg-type]
            completed_goal_ids=tuple(json.loads(record.completed_goal_ids_json)),
            summary=record.summary,
            tip=record.tip,
        )

    async def require_turn_capacity(self, session: ScenarioSession) -> None:
        if session.status != "active":
            raise ScenarioSessionInactiveError
        if len(session.turns) + 2 > MAX_PERSISTED_TURNS:
            raise ScenarioTurnLimitError

    async def append_pair(self, client_id: str, session_id: int, user: str, assistant: str) -> ScenarioSession:
        current = await self.get(client_id, session_id)
        await self.require_turn_capacity(current)
        idx = len(current.turns)
        self._session.add_all(
            [
                ScenarioTurnRecord(session_id=session_id, idx=idx, role="user", content=user),
                ScenarioTurnRecord(session_id=session_id, idx=idx + 1, role="assistant", content=assistant),
            ]
        )
        await self._session.commit()
        return await self.get(client_id, session_id)

    async def complete_atomic(
        self,
        client_id: str,
        scene: SceneDefinition,
        session_id: int,
        assessment: SceneAssessment,
    ) -> ScenarioCompletion:
        record = await self._session.scalar(
            select(ScenarioSessionRecord).where(
                ScenarioSessionRecord.id == session_id,
                ScenarioSessionRecord.client_id == client_id,
            )
        )
        if record is None:
            raise ScenarioSessionNotFoundError
        if record.status == "completed":
            return await self._completion_from_record(client_id, scene, record)

        learner_turn = await self._session.scalar(
            select(ScenarioTurnRecord.id).where(
                ScenarioTurnRecord.session_id == session_id,
                ScenarioTurnRecord.role == "user",
            ).limit(1)
        )
        if learner_turn is None:
            raise ScenarioCompletionRequiresLearnerError

        now = datetime.now(timezone.utc)
        ordered_ids = tuple(
            goal.id for goal in scene.goals if goal.id in assessment.completed_goal_ids
        )
        record.status = "completed"
        record.completed_goal_ids_json = json.dumps(ordered_ids, separators=(",", ":"))
        record.summary = assessment.summary
        record.tip = assessment.tip
        record.completed_at = now

        for goal_id in ordered_ids:
            progress = await self._session.scalar(
                select(SceneGoalProgressRecord).where(
                    SceneGoalProgressRecord.client_id == client_id,
                    SceneGoalProgressRecord.scene_id == scene.id,
                    SceneGoalProgressRecord.goal_id == goal_id,
                )
            )
            if progress is None:
                self._session.add(
                    SceneGoalProgressRecord(
                        client_id=client_id,
                        scene_id=scene.id,
                        goal_id=goal_id,
                        completion_count=1,
                        first_completed_at=now,
                        last_completed_at=now,
                    )
                )
            else:
                progress.completion_count += 1
                progress.last_completed_at = now
        await self._session.execute(
            delete(ScenarioTurnRecord).where(ScenarioTurnRecord.session_id == session_id)
        )
        await self._session.commit()
        return await self._completion_from_record(client_id, scene, record)

    async def completed_result(
        self, client_id: str, scene: SceneDefinition, session: ScenarioSession
    ) -> ScenarioCompletion:
        record = await self._session.get(ScenarioSessionRecord, session.id)
        if record is None or record.client_id != client_id:
            raise ScenarioSessionNotFoundError
        return await self._completion_from_record(client_id, scene, record)

    async def _completion_from_record(
        self, client_id: str, scene: SceneDefinition, record: ScenarioSessionRecord
    ) -> ScenarioCompletion:
        return ScenarioCompletion(
            session_id=record.id,
            scene_id=scene.id,
            completed_goal_ids=tuple(json.loads(record.completed_goal_ids_json)),
            summary=record.summary,
            tip=record.tip,
            progress=await self.progress(client_id, scene),
        )
