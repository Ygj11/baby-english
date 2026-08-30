"""Level-specific child tutor policy."""

from dataclasses import dataclass

from server.app.tutor.schemas import EnglishLevel


@dataclass(frozen=True, slots=True)
class ChildTutorPolicy:
    max_new_words: int
    allow_chinese_support: bool
    allow_simple_grammar: bool
    prefer_more_english: bool


def policy_for(level: EnglishLevel) -> ChildTutorPolicy:
    """Return the teaching constraints for a supported English level."""
    if level in {"starter", "beginner"}:
        return ChildTutorPolicy(
            max_new_words=3,
            allow_chinese_support=True,
            allow_simple_grammar=False,
            prefer_more_english=False,
        )

    return ChildTutorPolicy(
        max_new_words=3,
        allow_chinese_support=False,
        allow_simple_grammar=True,
        prefer_more_english=True,
    )
