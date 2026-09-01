"""Build child-safe tutor prompts from explicit policy."""

from server.app.tutor.child_policy import ChildTutorPolicy, policy_for
from server.app.tutor.schemas import StudentProfile


def build_system_prompt(student: StudentProfile) -> str:
    """Build the system prompt without provider-specific instructions."""
    policy = policy_for(student.english_level)
    rules = [
        "Keep the response short and focus on one main learning point.",
        f"Introduce no more than {policy.max_new_words} new words.",
        "Invite the student to repeat the key English aloud.",
        (
            "When you invite repetition, end the reply with exactly one marker in this "
            "form: Repeat after me: <English target>"
        ),
        (
            "The marker target must be 1 to 12 English words, with no Chinese, emoji, "
            "or text after the target. Do not use the marker when there is no clear target."
        ),
    ]
    rules.extend(_level_rules(policy))

    return "\n".join(
        [
            "You are an English tutor for a Chinese primary school student.",
            (
                f"The student is age {student.age}, grade {student.grade}, "
                f"at {student.english_level} level."
            ),
            "Teaching rules:",
            *(f"- {rule}" for rule in rules),
        ]
    )


def _level_rules(policy: ChildTutorPolicy) -> list[str]:
    if policy.allow_simple_grammar:
        return [
            "Use mostly English.",
            "You may explain simple grammar, such as singular and plural.",
            "Keep grammar explanations short.",
        ]

    return [
        "You may use brief Chinese support when it helps understanding.",
        "Avoid complex grammar terminology.",
    ]
