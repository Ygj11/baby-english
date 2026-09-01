"""Validation and stable fingerprinting for external textbook packages."""

import hashlib
import json
from pathlib import Path
import re
from typing import Any

from server.app.textbook.domain import (
    TextbookManifest,
    TextbookSource,
    TextbookSourceError,
    TextbookSourceRecord,
)


MANIFEST_FILE = "manifest.json"
MAX_RECORDS = 20_000
MAX_TEXT_CHARS = 12_000
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def load_textbook_source(package_dir: str | Path) -> TextbookSource:
    root = Path(package_dir).expanduser().resolve()
    if not root.is_dir():
        raise TextbookSourceError("The textbook package directory does not exist.")

    manifest_data = _load_json_object(root / MANIFEST_FILE, "manifest.json")
    _require_exact_keys(
        manifest_data,
        {
            "slug",
            "publisher",
            "series",
            "grade",
            "semester",
            "title",
            "version",
            "content_file",
        },
        "manifest.json",
    )
    manifest = TextbookManifest(
        slug=_bounded_string(manifest_data["slug"], "slug", 80),
        publisher=_bounded_string(manifest_data["publisher"], "publisher", 120),
        series=_bounded_string(manifest_data["series"], "series", 120),
        grade=_bounded_int(manifest_data["grade"], "grade", 1, 6),
        semester=_bounded_int(manifest_data["semester"], "semester", 1, 2),
        title=_bounded_string(manifest_data["title"], "title", 160),
        version=_bounded_string(manifest_data["version"], "version", 64),
        content_file=_bounded_string(manifest_data["content_file"], "content_file", 160),
    )
    if not SLUG_PATTERN.fullmatch(manifest.slug):
        raise TextbookSourceError("manifest.json field 'slug' is invalid.")

    content_path = _safe_content_path(root, manifest.content_file)
    records = _load_content_records(content_path)
    canonical = {
        "manifest": manifest_data,
        "records": [
            {
                "unit_no": item.unit_no,
                "unit_title": item.unit_title,
                "lesson": item.lesson,
                "page": item.page,
                "text": item.text,
            }
            for item in records
        ],
    }
    digest = hashlib.sha256(
        json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    return TextbookSource(manifest=manifest, records=records, source_sha256=digest)


def _load_content_records(path: Path) -> tuple[TextbookSourceRecord, ...]:
    try:
        handle = path.open("r", encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise TextbookSourceError("The textbook content file cannot be read as UTF-8.") from error

    records: list[TextbookSourceRecord] = []
    unit_titles: dict[int, str] = {}
    seen_records: set[tuple[int, str, str | None, int | None, str]] = set()
    try:
        with handle:
            for line_no, raw_line in enumerate(handle, start=1):
                if line_no > MAX_RECORDS:
                    raise TextbookSourceError(f"Content exceeds {MAX_RECORDS} records.")
                if not raw_line.strip():
                    raise TextbookSourceError(f"Content line {line_no} is blank.")
                try:
                    data = json.loads(raw_line)
                except json.JSONDecodeError as error:
                    raise TextbookSourceError(f"Content line {line_no} is invalid JSON.") from error
                if not isinstance(data, dict):
                    raise TextbookSourceError(f"Content line {line_no} must be a JSON object.")
                _require_allowed_keys(
                    data,
                    {"unit_no", "unit_title", "text"},
                    {"lesson", "page"},
                    f"content line {line_no}",
                )
                unit_no = _bounded_int(data["unit_no"], "unit_no", 1, 999, line_no)
                unit_title = _bounded_string(data["unit_title"], "unit_title", 160, line_no)
                text = _bounded_string(data["text"], "text", MAX_TEXT_CHARS, line_no)
                lesson = _optional_bounded_string(data.get("lesson"), "lesson", 160, line_no)
                page = (
                    _bounded_int(data["page"], "page", 1, 100_000, line_no)
                    if data.get("page") is not None
                    else None
                )
                prior_title = unit_titles.setdefault(unit_no, unit_title)
                if prior_title != unit_title:
                    raise TextbookSourceError(
                        f"Content line {line_no} conflicts with the title for unit {unit_no}."
                    )
                identity = (unit_no, unit_title, lesson, page, text)
                if identity in seen_records:
                    raise TextbookSourceError(f"Content line {line_no} duplicates an earlier record.")
                seen_records.add(identity)
                records.append(
                    TextbookSourceRecord(
                        unit_no=unit_no,
                        unit_title=unit_title,
                        lesson=lesson,
                        page=page,
                        text=text,
                        source_record=line_no,
                    )
                )
    except UnicodeError as error:
        raise TextbookSourceError("The textbook content file is not valid UTF-8.") from error
    if not records:
        raise TextbookSourceError("The textbook content file is empty.")
    return tuple(records)


def _safe_content_path(root: Path, relative_name: str) -> Path:
    candidate_name = Path(relative_name)
    if candidate_name.is_absolute():
        raise TextbookSourceError("content_file must be relative to the textbook package.")
    candidate = (root / candidate_name).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise TextbookSourceError("content_file must resolve to a file inside the package.")
    return candidate


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise TextbookSourceError(f"{label} is missing.") from error
    except OSError as error:
        raise TextbookSourceError(f"{label} cannot be read.") from error
    except UnicodeError as error:
        raise TextbookSourceError(f"{label} is not valid UTF-8.") from error
    except json.JSONDecodeError as error:
        raise TextbookSourceError(f"{label} is invalid JSON.") from error
    if not isinstance(value, dict):
        raise TextbookSourceError(f"{label} must contain a JSON object.")
    return value


def _require_exact_keys(value: dict[str, Any], required: set[str], label: str) -> None:
    if set(value) != required:
        raise TextbookSourceError(f"{label} has missing or unsupported fields.")


def _require_allowed_keys(
    value: dict[str, Any], required: set[str], optional: set[str], label: str
) -> None:
    if not required.issubset(value) or not set(value).issubset(required | optional):
        raise TextbookSourceError(f"{label} has missing or unsupported fields.")


def _bounded_string(value: Any, field: str, maximum: int, line: int | None = None) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        prefix = f"Content line {line}" if line is not None else "manifest.json"
        raise TextbookSourceError(f"{prefix} field '{field}' is invalid.")
    return value.strip()


def _optional_bounded_string(
    value: Any, field: str, maximum: int, line: int
) -> str | None:
    if value is None:
        return None
    return _bounded_string(value, field, maximum, line)


def _bounded_int(
    value: Any, field: str, minimum: int, maximum: int, line: int | None = None
) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        prefix = f"Content line {line}" if line is not None else "manifest.json"
        raise TextbookSourceError(f"{prefix} field '{field}' is invalid.")
    return value
