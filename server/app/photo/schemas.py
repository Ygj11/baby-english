"""Public Photo English API schemas."""

from pydantic import BaseModel, Field

from server.app.photo.domain import PhotoLearningResult


class RelatedWordResponse(BaseModel):
    word_en: str
    meaning_zh: str


class PhotoAnalysisResponse(BaseModel):
    status: str
    record_id: int | None = None
    primary_word_en: str | None = None
    primary_meaning_zh: str | None = None
    simple_sentence_en: str | None = None
    simple_sentence_zh: str | None = None
    practice_phrase: str | None = None
    related_words: list[RelatedWordResponse] = Field(default_factory=list)
    question_en: str | None = None
    encouragement_zh: str | None = None
    message_zh: str | None = None
    suggested_actions: list[str]


class PhotoListenResponse(BaseModel):
    audio_url: str


def analysis_response(result: PhotoLearningResult, record_id: int | None) -> PhotoAnalysisResponse:
    if result.status != "ok":
        return PhotoAnalysisResponse(
            status=result.status,
            record_id=None,
            message_zh=result.message_zh,
            suggested_actions=["retake"],
        )
    return PhotoAnalysisResponse(
        status="ok",
        record_id=record_id,
        primary_word_en=result.primary_word_en,
        primary_meaning_zh=result.primary_meaning_zh,
        simple_sentence_en=result.simple_sentence_en,
        simple_sentence_zh=result.simple_sentence_zh,
        practice_phrase=result.practice_phrase,
        related_words=[RelatedWordResponse(word_en=item.word_en, meaning_zh=item.meaning_zh) for item in result.related_words],
        question_en=result.question_en,
        encouragement_zh=result.encouragement_zh,
        suggested_actions=["listen", "repeat", "practice_chat"],
    )
