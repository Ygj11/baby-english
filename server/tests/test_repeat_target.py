from server.app.tutor.prompt_builder import build_system_prompt
from server.app.tutor.repeat_target import extract_repeat_target
from server.app.tutor.schemas import StudentProfile


def test_extracts_only_one_valid_marker_at_end() -> None:
    assert extract_repeat_target("Apple means 苹果. Repeat after me: apple") == "apple"
    assert (
        extract_repeat_target(
            "Let's practice. Repeat after me: Can I have some water, please?"
        )
        == "Can I have some water, please?"
    )
    assert extract_repeat_target("No explicit repeat target.") is None
    assert extract_repeat_target("Repeat after me: 香蕉") is None
    assert (
        extract_repeat_target("Repeat after me: apple Repeat after me: apple") is None
    )


def test_child_tutor_prompt_defines_stable_repeat_marker() -> None:
    prompt = build_system_prompt(
        StudentProfile(age=8, grade=3, english_level="beginner")
    )
    assert "Repeat after me: <English target>" in prompt
    assert "1 to 12 English words" in prompt
    assert "no Chinese, emoji" in prompt
