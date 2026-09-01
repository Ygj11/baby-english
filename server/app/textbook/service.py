"""Textbook-grounded question answering orchestration."""

from dataclasses import dataclass
from typing import Protocol

from server.app.textbook.domain import (
    RetrievedTextbookChunk,
    Textbook,
    TextbookAnswer,
    TextbookSourceLocation,
)
from server.app.textbook.prompt import build_textbook_prompt
from server.app.tutor.llm import LLMGateway
from server.app.tutor.schemas import StudentProfile


TEXTBOOK_NOT_FOUND_ANSWER = "这本课本当前内容里没有找到足够信息，我们换个问题试试吧。"
MAX_QUESTION_CHARS = 500


class TextbookRetrievalGateway(Protocol):
    async def retrieve(
        self, textbook: Textbook, *, question: str, unit_no: int | None
    ) -> tuple[RetrievedTextbookChunk, ...]: ...


@dataclass(slots=True)
class TextbookQAService:
    retriever: TextbookRetrievalGateway
    llm: LLMGateway

    async def answer(
        self,
        *,
        student: StudentProfile,
        textbook: Textbook,
        current_unit_no: int | None,
        question: str,
    ) -> TextbookAnswer:
        normalized = question.strip()
        if not normalized or len(normalized) > MAX_QUESTION_CHARS:
            raise ValueError("The textbook question is invalid.")
        retrieved = await self.retriever.retrieve(
            textbook, question=normalized, unit_no=current_unit_no
        )
        chunks = tuple(chunk for chunk in retrieved if chunk.text.strip())
        if not chunks:
            return TextbookAnswer(answer=TEXTBOOK_NOT_FOUND_ANSWER, sources=(), found=False)
        answer = await self.llm.generate(
            system_prompt=build_textbook_prompt(student, textbook, current_unit_no, chunks),
            message=normalized,
        )
        return TextbookAnswer(
            answer=answer,
            sources=_source_locations(chunks),
            found=True,
        )


def _source_locations(
    chunks: tuple[RetrievedTextbookChunk, ...],
) -> tuple[TextbookSourceLocation, ...]:
    sources: list[TextbookSourceLocation] = []
    seen: set[tuple[int, str, str | None, int | None]] = set()
    for chunk in chunks:
        identity = (chunk.unit_no, chunk.unit_title, chunk.lesson, chunk.page)
        if identity in seen:
            continue
        seen.add(identity)
        sources.append(
            TextbookSourceLocation(
                unit_no=chunk.unit_no,
                unit_title=chunk.unit_title,
                lesson=chunk.lesson,
                page=chunk.page,
            )
        )
    return tuple(sources)
