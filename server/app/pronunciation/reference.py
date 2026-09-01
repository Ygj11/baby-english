"""Deterministic English reference validation and ISE paper formatting."""

import re

from server.app.pronunciation.domain import EvaluationCategory


MAX_REFERENCE_CHARS = 200
MAX_REFERENCE_WORDS = 12
_WORD = r"[A-Za-z]+(?:[.'-][A-Za-z]+)*"
_SINGLE_WORD_PATTERN = re.compile(rf"^{_WORD}$")
_ALLOWED_REFERENCE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z .'!,?;:\-]*$")
_WORD_PATTERN = re.compile(_WORD)


class InvalidReferenceTextError(ValueError):
    """Raised when a repeat target cannot be sent to English ISE."""


def normalize_reference_text(value: str) -> str:
    reference = " ".join(value.strip().split())
    if not reference or len(reference) > MAX_REFERENCE_CHARS:
        raise InvalidReferenceTextError
    if not _ALLOWED_REFERENCE_PATTERN.fullmatch(reference):
        raise InvalidReferenceTextError
    words = _WORD_PATTERN.findall(reference)
    if not words or len(words) > MAX_REFERENCE_WORDS:
        raise InvalidReferenceTextError
    if any(len(word.encode("utf-8")) > 31 for word in words):
        raise InvalidReferenceTextError
    return reference


def choose_category(reference_text: str) -> EvaluationCategory:
    reference = normalize_reference_text(reference_text)
    return "read_word" if _SINGLE_WORD_PATTERN.fullmatch(reference) else "read_sentence"


def build_test_paper(
    reference_text: str,
    category: EvaluationCategory,
) -> str:
    reference = normalize_reference_text(reference_text)
    expected = choose_category(reference)
    if category != expected:
        raise InvalidReferenceTextError
    marker = "[word]" if category == "read_word" else "[content]"
    return f"\ufeff{marker}\n{reference}"
