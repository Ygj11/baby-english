"""Provider- and persistence-neutral scenario types."""

from dataclasses import dataclass
from typing import Literal


ScenarioRole = Literal["user", "assistant"]
ScenarioStatus = Literal["active", "completed"]


@dataclass(frozen=True, slots=True)
class SceneGoal:
    id: str
    title_zh: str
    practice_phrase: str
    hint_zh: str
    success_criteria: str


@dataclass(frozen=True, slots=True)
class SceneDefinition:
    id: str
    title: str
    title_zh: str
    subtitle: str
    icon: str
    difficulty: str
    partner_role: str
    opening_line: str
    persona: str
    goals: tuple[SceneGoal, ...]


@dataclass(frozen=True, slots=True)
class ScenarioMessage:
    role: ScenarioRole
    content: str


@dataclass(frozen=True, slots=True)
class SceneProgress:
    completed_goal_ids: tuple[str, ...]
    missing_goal_ids: tuple[str, ...]
    completed_count: int
    total_count: int


@dataclass(frozen=True, slots=True)
class ScenarioSession:
    id: int
    client_id: str
    scene_id: str
    status: ScenarioStatus
    turns: tuple[ScenarioMessage, ...]
    completed_goal_ids: tuple[str, ...] = ()
    summary: str = ""
    tip: str = ""


@dataclass(frozen=True, slots=True)
class SceneAssessment:
    completed_goal_ids: tuple[str, ...]
    summary: str
    tip: str


@dataclass(frozen=True, slots=True)
class ScenarioCompletion:
    session_id: int
    scene_id: str
    completed_goal_ids: tuple[str, ...]
    summary: str
    tip: str
    progress: SceneProgress
