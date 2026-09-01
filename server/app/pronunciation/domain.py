"""Provider-neutral pronunciation assessment types."""

from dataclasses import dataclass
from typing import Literal


EvaluationCategory = Literal["read_word", "read_sentence"]


@dataclass(frozen=True, slots=True)
class PronunciationIssue:
    kind: str
    unit: str | None = None


@dataclass(frozen=True, slots=True)
class WordPronunciationScore:
    word: str
    score: float | None
    issues: tuple[PronunciationIssue, ...] = ()


@dataclass(frozen=True, slots=True)
class PronunciationResult:
    overall_score: float
    accuracy_score: float
    fluency_score: float
    completeness_score: float | None
    standard_score: float | None
    rejected: bool
    words: tuple[WordPronunciationScore, ...] = ()
