"""Provider-neutral textbook domain objects and errors."""

from dataclasses import dataclass
from datetime import datetime


class TextbookError(RuntimeError):
    """Base error for the textbook feature."""


class TextbookSourceError(TextbookError):
    """Raised when an external textbook source package is unsafe or invalid."""


class TextbookConfigurationError(TextbookError):
    """Raised when textbook provider or index configuration is invalid."""


class TextbookIndexError(TextbookError):
    """Raised when a textbook index is unavailable, stale, or corrupt."""


@dataclass(frozen=True, slots=True)
class TextbookManifest:
    slug: str
    publisher: str
    series: str
    grade: int
    semester: int
    title: str
    version: str
    content_file: str


@dataclass(frozen=True, slots=True)
class TextbookSourceRecord:
    unit_no: int
    unit_title: str
    text: str
    source_record: int
    lesson: str | None = None
    page: int | None = None


@dataclass(frozen=True, slots=True)
class TextbookSource:
    manifest: TextbookManifest
    records: tuple[TextbookSourceRecord, ...]
    source_sha256: str


@dataclass(frozen=True, slots=True)
class Textbook:
    id: int
    slug: str
    publisher: str
    series: str
    grade: int
    semester: int
    title: str
    version: str
    source_sha256: str
    embedding_model: str
    embedding_dimensions: int
    index_schema_version: int
    indexed_at: datetime


@dataclass(frozen=True, slots=True)
class TextbookUnit:
    id: int
    textbook_id: int
    unit_no: int
    title: str


@dataclass(frozen=True, slots=True)
class StudentTextbookSelection:
    textbook: Textbook
    current_unit_no: int | None


@dataclass(frozen=True, slots=True)
class RetrievedTextbookChunk:
    text: str
    score: float | None
    unit_no: int
    unit_title: str
    lesson: str | None
    page: int | None
    source_record: int


@dataclass(frozen=True, slots=True)
class TextbookSourceLocation:
    unit_no: int
    unit_title: str
    lesson: str | None
    page: int | None


@dataclass(frozen=True, slots=True)
class TextbookAnswer:
    answer: str
    sources: tuple[TextbookSourceLocation, ...]
    found: bool
