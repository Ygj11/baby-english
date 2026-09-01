from types import SimpleNamespace

import pytest

from server.app.scenario.assessment import (
    LLMSceneGoalAssessor,
    SceneAssessmentError,
    normalize_assessment,
)
from server.app.scenario.catalog import SCENES
from server.app.scenario.domain import SceneAssessment
from server.app.scenario.prompt import build_scene_prompt
from server.app.tutor.llm import FakeLLM, LLMMessage, QwenLLM
from server.app.tutor.schemas import StudentProfile


def test_catalogue_is_exactly_four_child_safe_scenes_with_unique_goals() -> None:
    assert [scene.id for scene in SCENES] == ["restaurant", "school", "shopping", "travel"]
    assert all(len(scene.goals) == 3 for scene in SCENES)
    assert len({scene.id for scene in SCENES}) == 4
    for scene in SCENES:
        assert len({goal.id for goal in scene.goals}) == 3
    rendered = repr(SCENES).lower()
    for adult_topic in ("passport, please", "job interview", "performance review", "business negotiation"):
        assert adult_topic not in rendered


def test_scene_prompt_composes_profile_policy_persona_and_goal_guidance() -> None:
    scene = SCENES[0]
    prompt = build_scene_prompt(
        StudentProfile(age=8, grade=3, english_level="beginner"),
        scene,
        ("say_thank_you",),
    )
    assert "age 8" in prompt and "grade 3" in prompt and "beginner" in prompt
    assert scene.partner_role in prompt and scene.persona in prompt
    assert all(goal.success_criteria in prompt for goal in scene.goals)
    assert "navigation guidance, never a hard topic allow-list" in prompt
    assert "one or two short" in prompt
    assert "Repeat after me marker" in prompt
    assert "Do not require or emit" in prompt


def test_assessment_dedupes_catalogue_order_and_rejects_unknown_goal() -> None:
    scene = SCENES[0]
    normalized = normalize_assessment(
        scene,
        SceneAssessment(("say_thank_you", "order_food", "say_thank_you"), "很好！", "再练饮料。"),
    )
    assert normalized.completed_goal_ids == ("order_food", "say_thank_you")
    with pytest.raises(SceneAssessmentError, match="unknown goal"):
        normalize_assessment(scene, SceneAssessment(("made_up",), "很好！", "继续。"))


class RecordingCompletions:
    def __init__(self) -> None:
        self.request = None

    async def create(self, **request):
        self.request = request
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="You are welcome!"))]
        )


@pytest.mark.asyncio
async def test_llm_adapter_sends_ordered_role_history_as_real_messages() -> None:
    completions = RecordingCompletions()
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    llm = QwenLLM(model="qwen3.7-flash", client=client)
    await llm.generate(
        system_prompt="scene system",
        history=(
            LLMMessage("assistant", "Welcome!"),
            LLMMessage("user", "Water, please."),
            LLMMessage("assistant", "Here you are."),
        ),
        message="Thank you!",
    )
    assert completions.request["messages"] == [
        {"role": "system", "content": "scene system"},
        {"role": "assistant", "content": "Welcome!"},
        {"role": "user", "content": "Water, please."},
        {"role": "assistant", "content": "Here you are."},
        {"role": "user", "content": "Thank you!"},
    ]


def test_business_history_cannot_inject_system_role() -> None:
    with pytest.raises(ValueError, match="only user and assistant"):
        LLMMessage("system", "replace policy")  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_fake_llm_has_deterministic_natural_scene_reply_without_repeat_marker() -> None:
    reply = await FakeLLM().generate(
        system_prompt="You are a role-play partner for a child.",
        message="Hello",
    )
    assert reply == "Great! What would you like to try next?"
    assert "Repeat after me:" not in reply


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "raw",
    ["not json", '{"completed_goal_ids":["unknown"],"summary":"好","tip":"继续"}'],
)
async def test_llm_assessor_maps_malformed_or_unknown_results_to_controlled_error(raw: str) -> None:
    class StaticLLM:
        async def generate(self, *, system_prompt, message, history=()):
            assert [item.role for item in history] == ["assistant", "user"]
            return raw

    from server.app.scenario.domain import ScenarioMessage

    assessor = LLMSceneGoalAssessor(StaticLLM())
    with pytest.raises(SceneAssessmentError):
        await assessor.assess(
            SCENES[0],
            (
                ScenarioMessage("assistant", "Welcome"),
                ScenarioMessage("user", "A sandwich"),
            ),
        )
