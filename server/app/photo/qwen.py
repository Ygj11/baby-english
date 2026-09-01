"""Qwen multimodal adapter with strict Pydantic structured output."""

import base64
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from openai import OpenAIError
from pydantic import BaseModel, ConfigDict

from server.app.photo.domain import PhotoLearningResult, RelatedWord
from server.app.photo.gateway import VisionError


class _ProviderRelatedWord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    word_en: str
    meaning_zh: str


class _ProviderPhotoResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "unclear", "unsuitable"]
    primary_word_en: str | None
    primary_meaning_zh: str | None
    simple_sentence_en: str | None
    simple_sentence_zh: str | None
    practice_phrase: str | None
    related_words: list[_ProviderRelatedWord]
    question_en: str | None
    encouragement_zh: str | None
    message_zh: str | None


@dataclass(slots=True)
class QwenVision:
    model: str
    client: Any = field(repr=False)

    async def analyze(self, *, image_path: Path, system_prompt: str) -> PhotoLearningResult:
        try:
            encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
            response = await self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
                            },
                            {
                                "type": "text",
                                "text": "Create one safe, small English lesson from this image.",
                            },
                        ],
                    },
                ],
                response_format=_ProviderPhotoResult,
            )
            parsed = response.choices[0].message.parsed
        except (OpenAIError, TimeoutError, OSError) as error:
            raise VisionError("The Vision provider request failed.") from error
        except (AttributeError, IndexError, TypeError, ValueError) as error:
            raise VisionError("The Vision provider returned an invalid response.") from error

        if not isinstance(parsed, _ProviderPhotoResult):
            raise VisionError("The Vision provider returned an invalid response.")
        return PhotoLearningResult(
            status=parsed.status,
            primary_word_en=parsed.primary_word_en,
            primary_meaning_zh=parsed.primary_meaning_zh,
            simple_sentence_en=parsed.simple_sentence_en,
            simple_sentence_zh=parsed.simple_sentence_zh,
            practice_phrase=parsed.practice_phrase,
            related_words=tuple(
                RelatedWord(word_en=item.word_en, meaning_zh=item.meaning_zh)
                for item in parsed.related_words
            ),
            question_en=parsed.question_en,
            encouragement_zh=parsed.encouragement_zh,
            message_zh=parsed.message_zh,
        )


ProviderPhotoResult = _ProviderPhotoResult
