"""HTTP schemas for textbook catalogue, selection, and grounded Q&A."""

from pydantic import BaseModel, ConfigDict, Field

from server.app.textbook.domain import (
    StudentTextbookSelection,
    Textbook,
    TextbookAnswer,
    TextbookSourceLocation,
    TextbookUnit,
)


class TextbookSummaryResponse(BaseModel):
    id: int
    title: str
    publisher: str
    series: str
    grade: int
    semester: int
    version: str
    selected: bool


class TextbookUnitResponse(BaseModel):
    unit_no: int
    title: str


class CurrentTextbookResponse(BaseModel):
    textbook: TextbookSummaryResponse | None
    current_unit_no: int | None
    units: list[TextbookUnitResponse]


class SelectTextbookRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    textbook_id: int = Field(gt=0)
    current_unit_no: int | None = Field(default=None, gt=0)


class AskTextbookRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=500)


class TextbookSourceResponse(BaseModel):
    unit_no: int
    unit_title: str
    lesson: str | None
    page: int | None


class AskTextbookResponse(BaseModel):
    answer: str
    found: bool
    sources: list[TextbookSourceResponse]


def summary_response(textbook: Textbook, *, selected: bool) -> TextbookSummaryResponse:
    return TextbookSummaryResponse(
        id=textbook.id,
        title=textbook.title,
        publisher=textbook.publisher,
        series=textbook.series,
        grade=textbook.grade,
        semester=textbook.semester,
        version=textbook.version,
        selected=selected,
    )


def current_response(
    selection: StudentTextbookSelection | None,
    units: tuple[TextbookUnit, ...] = (),
) -> CurrentTextbookResponse:
    if selection is None:
        return CurrentTextbookResponse(textbook=None, current_unit_no=None, units=[])
    return CurrentTextbookResponse(
        textbook=summary_response(selection.textbook, selected=True),
        current_unit_no=selection.current_unit_no,
        units=[TextbookUnitResponse(unit_no=item.unit_no, title=item.title) for item in units],
    )


def answer_response(answer: TextbookAnswer) -> AskTextbookResponse:
    return AskTextbookResponse(
        answer=answer.answer,
        found=answer.found,
        sources=[_source_response(item) for item in answer.sources],
    )


def _source_response(source: TextbookSourceLocation) -> TextbookSourceResponse:
    return TextbookSourceResponse(
        unit_no=source.unit_no,
        unit_title=source.unit_title,
        lesson=source.lesson,
        page=source.page,
    )
