"""Slow-path structured scene-goal assessment."""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from server.app.scenario.domain import SceneAssessment, SceneDefinition, ScenarioMessage
from server.app.tutor.llm import FakeLLM, LLMGateway, LLMMessage, create_llm


class SceneAssessmentError(RuntimeError):
    pass


class SceneGoalAssessor(Protocol):
    async def assess(
        self, scene: SceneDefinition, transcript: Sequence[ScenarioMessage]
    ) -> SceneAssessment: ...


@dataclass(slots=True)
class FakeSceneGoalAssessor:
    completed_goal_ids: tuple[str, ...] = ()
    summary: str = "练习完成！你勇敢地用英语交流了。"
    tip: str = "下次可以再试一个新的场景目标。"
    calls: int = 0

    async def assess(
        self, scene: SceneDefinition, transcript: Sequence[ScenarioMessage]
    ) -> SceneAssessment:
        self.calls += 1
        return normalize_assessment(
            scene,
            SceneAssessment(self.completed_goal_ids, self.summary, self.tip),
        )


@dataclass(slots=True)
class LLMSceneGoalAssessor:
    llm: LLMGateway

    async def assess(
        self, scene: SceneDefinition, transcript: Sequence[ScenarioMessage]
    ) -> SceneAssessment:
        criteria = "\n".join(
            f"- {goal.id}: {goal.success_criteria}" for goal in scene.goals
        )
        prompt = "\n".join(
            [
                "Assess only evidence in learner/user turns from this child role-play.",
                "Communicative success matters more than perfect grammar or exact phrase matching.",
                "Return one JSON object only with completed_goal_ids, summary, and tip.",
                "completed_goal_ids must contain only supported IDs; summary and tip must be short encouraging Chinese strings.",
                "Goals:",
                criteria,
            ]
        )
        history = tuple(
            LLMMessage(role=message.role, content=message.content)
            for message in transcript
        )
        raw = await self.llm.generate(
            system_prompt=prompt,
            history=history,
            message="Assess this completed scene now and return JSON only.",
        )
        try:
            data = json.loads(raw)
            ids = data["completed_goal_ids"]
            summary = data["summary"]
            tip = data["tip"]
            if not isinstance(ids, list) or not all(isinstance(item, str) for item in ids):
                raise TypeError
            if not isinstance(summary, str) or not isinstance(tip, str):
                raise TypeError
        except (json.JSONDecodeError, KeyError, TypeError) as error:
            raise SceneAssessmentError("Scene assessment returned invalid JSON.") from error
        return normalize_assessment(scene, SceneAssessment(tuple(ids), summary, tip))


def normalize_assessment(
    scene: SceneDefinition, assessment: SceneAssessment
) -> SceneAssessment:
    valid = {goal.id for goal in scene.goals}
    if any(goal_id not in valid for goal_id in assessment.completed_goal_ids):
        raise SceneAssessmentError("Scene assessment returned an unknown goal.")
    summary = assessment.summary.strip()
    tip = assessment.tip.strip()
    if not summary or not tip or len(summary) > 300 or len(tip) > 300:
        raise SceneAssessmentError("Scene assessment returned invalid feedback.")
    deduped = tuple(
        goal.id for goal in scene.goals if goal.id in assessment.completed_goal_ids
    )
    return SceneAssessment(deduped, summary, tip)


def create_scene_goal_assessor() -> SceneGoalAssessor:
    llm = create_llm()
    if isinstance(llm, FakeLLM):
        return FakeSceneGoalAssessor()
    return LLMSceneGoalAssessor(llm)
