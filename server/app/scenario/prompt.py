"""Compose a child-safe role-play prompt from current product facts."""

from server.app.scenario.domain import SceneDefinition
from server.app.tutor.child_policy import policy_for
from server.app.tutor.schemas import StudentProfile


def build_scene_prompt(
    student: StudentProfile,
    scene: SceneDefinition,
    completed_goal_ids: tuple[str, ...],
) -> str:
    policy = policy_for(student.english_level)
    remaining = [goal for goal in scene.goals if goal.id not in completed_goal_ids]
    goals = "\n".join(
        f"- {goal.id}: {goal.success_criteria} (practice phrase: {goal.practice_phrase})"
        for goal in scene.goals
    )
    remaining_ids = ", ".join(goal.id for goal in remaining) or "none"
    chinese_support = (
        "Very brief Chinese support is allowed only when the learner is genuinely stuck."
        if policy.allow_chinese_support
        else "Use English only unless safety requires otherwise."
    )
    return "\n".join(
        [
            "You are a role-play partner for a Chinese primary-school English learner.",
            f"The learner is age {student.age}, grade {student.grade}, level {student.english_level}.",
            f"Scene: {scene.title}. Your role: {scene.partner_role}.",
            f"Internal persona: {scene.persona}",
            "Learning goals (navigation guidance, never a hard topic allow-list):",
            goals,
            f"Goals not yet completed in prior sessions: {remaining_ids}.",
            "Stay in role and naturally steer toward unfinished goals.",
            "Reply with one or two short, speakable sentences and usually one simple question.",
            f"When helping, introduce no more than {policy.max_new_words} new words at once.",
            "Prefer mostly English." if policy.prefer_more_english else "Keep English simple and concrete.",
            chinese_support,
            "If the child goes briefly off-topic, answer simply and gently return to the scene.",
            "Do not grade or correct every turn. Do not require or emit a Repeat after me marker.",
            "Never request a real full name, school name, address, phone, passport, payment or account information.",
            "Keep everything fictional, child-safe, and free of adult medical, legal, financial or workplace situations.",
        ]
    )
