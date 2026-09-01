"""Provider-neutral Photo English result and last-line validation."""

from dataclasses import dataclass, replace
import re
from typing import Literal


PhotoLearningStatus = Literal["ok", "unclear", "unsuitable"]

UNCLEAR_MESSAGE_ZH = "这张照片有点看不清，换个角度再拍一次吧。"
UNSUITABLE_MESSAGE_ZH = "我们换一张动物、食物、玩具或学习用品的照片来学英语吧。"

_ENGLISH_TEXT = re.compile(r"^[A-Za-z][A-Za-z '\-.,!?]*$")
_URL = re.compile(r"(?:https?://|www\.)", re.IGNORECASE)
_EMAIL = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
_LONG_NUMBER = re.compile(r"(?<!\d)\d(?:[\s()-]*\d){6,}(?!\d)")


class InvalidPhotoLearningResultError(ValueError):
    """Raised when provider output is structurally unsafe or unusable."""


@dataclass(frozen=True, slots=True)
class RelatedWord:
    word_en: str
    meaning_zh: str


@dataclass(frozen=True, slots=True)
class PhotoLearningResult:
    status: PhotoLearningStatus
    primary_word_en: str | None = None
    primary_meaning_zh: str | None = None
    simple_sentence_en: str | None = None
    simple_sentence_zh: str | None = None
    practice_phrase: str | None = None
    related_words: tuple[RelatedWord, ...] = ()
    question_en: str | None = None
    encouragement_zh: str | None = None
    message_zh: str | None = None


def validate_learning_result(result: PhotoLearningResult) -> PhotoLearningResult:
    """Normalize one provider result and prevent obvious private data storage."""
    if result.status == "unclear":
        return PhotoLearningResult(status="unclear", message_zh=UNCLEAR_MESSAGE_ZH)
    if result.status == "unsuitable":
        return PhotoLearningResult(status="unsuitable", message_zh=UNSUITABLE_MESSAGE_ZH)
    if result.status != "ok":
        raise InvalidPhotoLearningResultError("Unknown photo learning status.")

    if _contains_sensitive(result):
        return PhotoLearningResult(status="unsuitable", message_zh=UNSUITABLE_MESSAGE_ZH)

    required = {
        "primary_word_en": result.primary_word_en,
        "primary_meaning_zh": result.primary_meaning_zh,
        "simple_sentence_en": result.simple_sentence_en,
        "simple_sentence_zh": result.simple_sentence_zh,
        "practice_phrase": result.practice_phrase,
        "question_en": result.question_en,
        "encouragement_zh": result.encouragement_zh,
    }
    if any(not isinstance(value, str) or not value.strip() for value in required.values()):
        raise InvalidPhotoLearningResultError("A required lesson field is blank.")

    normalized = replace(
        result,
        primary_word_en=result.primary_word_en.strip(),  # type: ignore[union-attr]
        primary_meaning_zh=result.primary_meaning_zh.strip(),  # type: ignore[union-attr]
        simple_sentence_en=result.simple_sentence_en.strip(),  # type: ignore[union-attr]
        simple_sentence_zh=result.simple_sentence_zh.strip(),  # type: ignore[union-attr]
        practice_phrase=result.practice_phrase.strip(),  # type: ignore[union-attr]
        question_en=result.question_en.strip(),  # type: ignore[union-attr]
        encouragement_zh=result.encouragement_zh.strip(),  # type: ignore[union-attr]
        related_words=tuple(
            RelatedWord(item.word_en.strip(), item.meaning_zh.strip())
            for item in result.related_words
        ),
        message_zh=None,
    )

    limits = {
        "primary_word_en": 48,
        "primary_meaning_zh": 48,
        "simple_sentence_en": 180,
        "simple_sentence_zh": 120,
        "practice_phrase": 80,
        "question_en": 180,
        "encouragement_zh": 120,
    }
    for field_name, limit in limits.items():
        value = getattr(normalized, field_name)
        if len(value) > limit:
            raise InvalidPhotoLearningResultError(f"{field_name} is too long.")

    if len(normalized.related_words) > 4:
        raise InvalidPhotoLearningResultError("Too many related words.")
    if not _valid_english(normalized.primary_word_en, max_words=4):
        raise InvalidPhotoLearningResultError("Primary word is invalid.")
    if not _valid_english(normalized.practice_phrase, max_words=8):
        raise InvalidPhotoLearningResultError("Practice phrase is invalid.")
    if not _ENGLISH_TEXT.fullmatch(normalized.simple_sentence_en):
        raise InvalidPhotoLearningResultError("English sentence is invalid.")
    if not _ENGLISH_TEXT.fullmatch(normalized.question_en):
        raise InvalidPhotoLearningResultError("English question is invalid.")

    vocabulary = {normalized.primary_word_en.casefold()}
    for item in normalized.related_words:
        if not item.word_en or not item.meaning_zh:
            raise InvalidPhotoLearningResultError("Related word is blank.")
        if len(item.word_en) > 48 or len(item.meaning_zh) > 48:
            raise InvalidPhotoLearningResultError("Related word is too long.")
        if not _valid_english(item.word_en, max_words=4):
            raise InvalidPhotoLearningResultError("Related word is invalid.")
        key = item.word_en.casefold()
        if key in vocabulary:
            raise InvalidPhotoLearningResultError("Vocabulary is duplicated.")
        vocabulary.add(key)

    return normalized


def _valid_english(value: str, *, max_words: int) -> bool:
    return bool(_ENGLISH_TEXT.fullmatch(value)) and 1 <= len(value.split()) <= max_words


def _contains_sensitive(result: PhotoLearningResult) -> bool:
    values = [
        result.primary_word_en,
        result.primary_meaning_zh,
        result.simple_sentence_en,
        result.simple_sentence_zh,
        result.practice_phrase,
        result.question_en,
        result.encouragement_zh,
        result.message_zh,
    ]
    values.extend(
        value
        for item in result.related_words
        for value in (item.word_en, item.meaning_zh)
    )
    all_text = " ".join(value for value in values if isinstance(value, str))
    return bool(
        _URL.search(all_text) or _EMAIL.search(all_text) or _LONG_NUMBER.search(all_text)
    )
