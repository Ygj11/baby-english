import json
from pathlib import Path

import pytest

from server.app.textbook.domain import TextbookSourceError
from server.app.textbook.source import load_textbook_source


def write_package(
    root: Path,
    *,
    manifest_changes: dict | None = None,
    lines: list[dict | str] | None = None,
) -> Path:
    root.mkdir()
    manifest = {
        "slug": "synthetic-english-3a",
        "publisher": "Synthetic Learning Press",
        "series": "Tiny English",
        "grade": 3,
        "semester": 1,
        "title": "Synthetic English 3A",
        "version": "2026-test",
        "content_file": "content.jsonl",
    }
    manifest.update(manifest_changes or {})
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    if lines is not None:
        (root / "content.jsonl").write_text(
            "\n".join(item if isinstance(item, str) else json.dumps(item) for item in lines) + "\n",
            encoding="utf-8",
        )
    return root


def valid_lines() -> list[dict]:
    return [
        {
            "unit_no": 1,
            "unit_title": "Toy Friends",
            "lesson": "Lesson 1",
            "page": 4,
            "text": "Milo is a small blue bear. Milo likes red apples.",
        },
        {
            "unit_no": 1,
            "unit_title": "Toy Friends",
            "lesson": "Lesson 2",
            "page": 6,
            "text": "Milo says hello to a yellow bird.",
        },
    ]


def test_valid_package_and_stable_fingerprint(tmp_path: Path) -> None:
    package = write_package(tmp_path / "book", lines=valid_lines())
    first = load_textbook_source(package)
    second = load_textbook_source(package)
    assert first.manifest.slug == "synthetic-english-3a"
    assert first.records[0].source_record == 1
    assert first.source_sha256 == second.source_sha256
    assert len(first.source_sha256) == 64


@pytest.mark.parametrize(
    ("manifest_changes", "lines"),
    [
        ({"grade": 0}, valid_lines()),
        ({"semester": 3}, valid_lines()),
        ({}, [{"unit_no": 0, "unit_title": "U", "text": "text"}]),
        ({}, [{"unit_no": 1, "unit_title": "U", "text": "text", "page": -1}]),
        ({}, [{"unit_no": 1, "unit_title": "U", "text": "   "}]),
    ],
)
def test_invalid_bounded_fields_are_rejected(
    tmp_path: Path, manifest_changes: dict, lines: list[dict]
) -> None:
    package = write_package(tmp_path / "book", manifest_changes=manifest_changes, lines=lines)
    with pytest.raises(TextbookSourceError):
        load_textbook_source(package)


def test_invalid_manifest_json_and_jsonl_report_safe_line(tmp_path: Path) -> None:
    package = write_package(tmp_path / "bad_manifest", lines=valid_lines())
    (package / "manifest.json").write_text("{bad", encoding="utf-8")
    with pytest.raises(TextbookSourceError, match="manifest.json is invalid JSON"):
        load_textbook_source(package)

    package = write_package(tmp_path / "bad_jsonl", lines=[valid_lines()[0], "{bad"])
    with pytest.raises(TextbookSourceError, match="line 2 is invalid JSON") as captured:
        load_textbook_source(package)
    assert str(package) not in str(captured.value)


def test_missing_content_and_path_traversal_are_rejected(tmp_path: Path) -> None:
    missing = write_package(tmp_path / "missing", lines=None)
    with pytest.raises(TextbookSourceError, match="inside the package"):
        load_textbook_source(missing)
    outside = tmp_path / "outside.jsonl"
    outside.write_text("{}\n", encoding="utf-8")
    traversal = write_package(
        tmp_path / "traversal",
        manifest_changes={"content_file": "../outside.jsonl"},
        lines=None,
    )
    with pytest.raises(TextbookSourceError, match="inside the package"):
        load_textbook_source(traversal)


def test_duplicate_and_conflicting_unit_metadata_are_rejected(tmp_path: Path) -> None:
    duplicate = write_package(tmp_path / "duplicate", lines=[valid_lines()[0], valid_lines()[0]])
    with pytest.raises(TextbookSourceError, match="duplicates"):
        load_textbook_source(duplicate)
    conflict_lines = valid_lines()
    conflict_lines[1] = {**conflict_lines[1], "unit_title": "Different Unit"}
    conflict = write_package(tmp_path / "conflict", lines=conflict_lines)
    with pytest.raises(TextbookSourceError, match="conflicts"):
        load_textbook_source(conflict)


def test_repository_contains_no_textbook_source_package() -> None:
    repository = Path(__file__).resolve().parents[2]
    assert not list(repository.glob("**/manifest.json"))
    assert not list(repository.glob("**/content.jsonl"))
