"""Profile-aware textbook catalogue, selection, and grounded Q&A endpoints."""

import logging
from time import perf_counter
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from server.app.api.dependencies import get_client_id
from server.app.persistence.database import SessionFactory
from server.app.student_profile.repository import SQLAlchemyStudentProfileRepository
from server.app.student_profile.service import StudentProfileService
from server.app.textbook.domain import TextbookConfigurationError, TextbookIndexError
from server.app.textbook.embedding import create_textbook_embedding
from server.app.textbook.repository import (
    SQLAlchemyStudentTextbookRepository,
    SQLAlchemyTextbookRepository,
)
from server.app.textbook.retriever import TextbookRetriever
from server.app.textbook.schemas import (
    AskTextbookRequest,
    AskTextbookResponse,
    CurrentTextbookResponse,
    SelectTextbookRequest,
    TextbookSummaryResponse,
    TextbookUnitResponse,
    answer_response,
    current_response,
    summary_response,
)
from server.app.textbook.service import TextbookQAService
from server.app.tutor.llm import LLMConfigurationError, LLMError, create_llm
from server.app.tutor.schemas import StudentProfile


router = APIRouter(prefix="/api/textbooks", tags=["textbooks"])
logger = logging.getLogger("uvicorn.error.baby_english.textbook")


async def require_textbook_profile(
    client_id: Annotated[str, Depends(get_client_id)],
) -> StudentProfile:
    async with SessionFactory() as session:
        profile = await StudentProfileService(
            SQLAlchemyStudentProfileRepository(session)
        ).get(client_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student profile setup is required.",
        )
    return profile


@router.get("", response_model=list[TextbookSummaryResponse])
async def list_textbooks(
    client_id: Annotated[str, Depends(get_client_id)],
    _student: Annotated[StudentProfile, Depends(require_textbook_profile)],
) -> list[TextbookSummaryResponse]:
    async with SessionFactory() as session:
        books = await SQLAlchemyTextbookRepository(session).list_ready()
        selection = await SQLAlchemyStudentTextbookRepository(session).get_current(client_id)
    selected_id = selection.textbook.id if selection is not None else None
    return [summary_response(book, selected=book.id == selected_id) for book in books]


@router.get("/current", response_model=CurrentTextbookResponse)
async def get_current_textbook(
    client_id: Annotated[str, Depends(get_client_id)],
    _student: Annotated[StudentProfile, Depends(require_textbook_profile)],
) -> CurrentTextbookResponse:
    async with SessionFactory() as session:
        selection = await SQLAlchemyStudentTextbookRepository(session).get_current(client_id)
        units = (
            await SQLAlchemyTextbookRepository(session).list_units(selection.textbook.id)
            if selection is not None
            else ()
        )
    return current_response(selection, units)


@router.put("/current", response_model=CurrentTextbookResponse)
async def select_current_textbook(
    payload: SelectTextbookRequest,
    client_id: Annotated[str, Depends(get_client_id)],
    _student: Annotated[StudentProfile, Depends(require_textbook_profile)],
) -> CurrentTextbookResponse:
    async with SessionFactory() as session:
        selection = await SQLAlchemyStudentTextbookRepository(session).select(
            client_id, payload.textbook_id, payload.current_unit_no
        )
        if selection is None:
            raise HTTPException(status_code=404, detail="Textbook or unit not found.")
        units = await SQLAlchemyTextbookRepository(session).list_units(selection.textbook.id)
    return current_response(selection, units)


@router.post("/ask", response_model=AskTextbookResponse)
async def ask_textbook(
    payload: AskTextbookRequest,
    client_id: Annotated[str, Depends(get_client_id)],
    student: Annotated[StudentProfile, Depends(require_textbook_profile)],
) -> AskTextbookResponse:
    # Load selection in a short session, then close it before embedding or LLM calls.
    async with SessionFactory() as session:
        selection = await SQLAlchemyStudentTextbookRepository(session).get_current(client_id)
    if selection is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Select a textbook before asking a question.",
        )

    started = perf_counter()
    try:
        embedding = create_textbook_embedding()
        service = TextbookQAService(
            retriever=TextbookRetriever(embedding),
            llm=create_llm(),
        )
        answer = await service.answer(
            student=student,
            textbook=selection.textbook,
            current_unit_no=selection.current_unit_no,
            question=payload.question,
        )
    except ValueError:
        raise HTTPException(status_code=422, detail="The textbook question is invalid.") from None
    except (TextbookConfigurationError, TextbookIndexError, LLMConfigurationError, LLMError) as error:
        logger.warning(
            "provider_failure stage=textbook category=request exception=%s",
            type(error).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Textbook learning is temporarily unavailable.",
        ) from None
    logger.info("textbook_qa_latency total_ms=%d", round((perf_counter() - started) * 1000))
    return answer_response(answer)


@router.get("/{textbook_id}/units", response_model=list[TextbookUnitResponse])
async def list_textbook_units(
    textbook_id: int,
    _client_id: Annotated[str, Depends(get_client_id)],
    _student: Annotated[StudentProfile, Depends(require_textbook_profile)],
) -> list[TextbookUnitResponse]:
    async with SessionFactory() as session:
        textbook = await SQLAlchemyTextbookRepository(session).get_ready(textbook_id)
        if textbook is None:
            raise HTTPException(status_code=404, detail="Textbook not found.")
        units = await SQLAlchemyTextbookRepository(session).list_units(textbook_id)
    return [TextbookUnitResponse(unit_no=item.unit_no, title=item.title) for item in units]
