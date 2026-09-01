"""Tutor chat API."""

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from server.app.api.dependencies import require_student_profile
from server.app.tutor.llm import LLMConfigurationError, LLMError, create_llm
from server.app.tutor.repeat_target import extract_repeat_target
from server.app.tutor.schemas import StudentProfile
from server.app.tutor.service import TutorService

router = APIRouter(prefix="/api/tutor", tags=["tutor"])
logger = logging.getLogger("uvicorn.error.baby_english.tutor")


class ChatContext(BaseModel):
    mode: Literal["chat"]


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=2000)
    context: ChatContext

    @field_validator("message", mode="before")
    @classmethod
    def trim_message(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class ChatResponse(BaseModel):
    reply: str
    repeat_text: str | None
    language: str
    suggested_actions: list[str]


def get_tutor_service() -> TutorService:
    try:
        return TutorService(llm=create_llm())
    except LLMConfigurationError as error:
        logger.warning(
            "provider_failure stage=llm category=configuration exception=%s",
            type(error).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tutor is temporarily unavailable.",
        ) from None


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    student: Annotated[StudentProfile, Depends(require_student_profile)],
    service: Annotated[TutorService, Depends(get_tutor_service)],
) -> ChatResponse:
    try:
        reply = await service.reply(request.message, student)
    except LLMError as error:
        logger.warning(
            "provider_failure stage=llm category=request exception=%s",
            type(error).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tutor is temporarily unavailable.",
        ) from None

    repeat_text = extract_repeat_target(reply)
    actions = ["explain_zh"]
    if repeat_text is not None:
        actions.insert(0, "repeat")
    return ChatResponse(
        reply=reply,
        repeat_text=repeat_text,
        language="mixed",
        suggested_actions=actions,
    )
