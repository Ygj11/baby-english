"""Public API schemas for scenario English."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from server.app.scenario.domain import SceneDefinition, SceneProgress


class SceneProgressResponse(BaseModel):
    completed_goal_ids: list[str]
    missing_goal_ids: list[str]
    completed_count: int
    total_count: int


class SceneGoalResponse(BaseModel):
    id: str
    title_zh: str
    practice_phrase: str
    hint_zh: str


class SceneResponse(BaseModel):
    id: str
    title: str
    title_zh: str
    subtitle: str
    icon: str
    difficulty: str
    partner_role: str
    opening_line: str
    goals: list[SceneGoalResponse]
    progress: SceneProgressResponse


class StartSessionResponse(BaseModel):
    session_id: int
    scene: SceneResponse
    opening_message: str
    progress: SceneProgressResponse


class ScenarioTurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=600)

    @field_validator("message", mode="before")
    @classmethod
    def trim_message(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ScenarioTurnResponse(BaseModel):
    session_id: int
    reply: str


class ScenarioVoiceTurnResponse(ScenarioTurnResponse):
    transcript: str
    audio_url: str


class ScenarioCompletionResponse(BaseModel):
    session_id: int
    scene_id: str
    completed_goal_ids: list[str]
    summary: str
    tip: str
    progress: SceneProgressResponse


def progress_response(progress: SceneProgress) -> SceneProgressResponse:
    return SceneProgressResponse(
        completed_goal_ids=list(progress.completed_goal_ids),
        missing_goal_ids=list(progress.missing_goal_ids),
        completed_count=progress.completed_count,
        total_count=progress.total_count,
    )


def scene_response(scene: SceneDefinition, progress: SceneProgress) -> SceneResponse:
    return SceneResponse(
        id=scene.id,
        title=scene.title,
        title_zh=scene.title_zh,
        subtitle=scene.subtitle,
        icon=scene.icon,
        difficulty=scene.difficulty,
        partner_role=scene.partner_role,
        opening_line=scene.opening_line,
        goals=[
            SceneGoalResponse(
                id=goal.id,
                title_zh=goal.title_zh,
                practice_phrase=goal.practice_phrase,
                hint_zh=goal.hint_zh,
            )
            for goal in scene.goals
        ],
        progress=progress_response(progress),
    )
