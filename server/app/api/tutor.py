"""Tutor chat API."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from server.app.tutor.llm import LLMConfigurationError, LLMError, create_llm
from server.app.tutor.schemas import EnglishLevel, StudentProfile
from server.app.tutor.service import TutorService

router = APIRouter(prefix="/api/tutor", tags=["tutor"])


class StudentInput(BaseModel):
    age: int = Field(ge=5, le=15)
    grade: int = Field(ge=1, le=9)
    english_level: EnglishLevel


class ChatContext(BaseModel):
    mode: Literal["chat"]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    student: StudentInput
    context: ChatContext

    @field_validator("message", mode="before")
    @classmethod
    def trim_message(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class ChatResponse(BaseModel):
    reply: str
    language: str
    suggested_actions: list[str]


def get_tutor_service() -> TutorService:
    try:
        return TutorService(llm=create_llm())
    except LLMConfigurationError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tutor is temporarily unavailable.",
        ) from None


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    service: Annotated[TutorService, Depends(get_tutor_service)],
) -> ChatResponse:
    try:
        reply = await service.reply(
            request.message,
            StudentProfile(
                age=request.student.age,
                grade=request.student.grade,
                english_level=request.student.english_level,
            ),
        )
    except LLMError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tutor is temporarily unavailable.",
        ) from None

    return ChatResponse(
        reply=reply,
        language="mixed",
        suggested_actions=["repeat", "explain_zh"],
    )
