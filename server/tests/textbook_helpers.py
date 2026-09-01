import json
from pathlib import Path

from server.app.textbook.source import load_textbook_source


def synthetic_source(root: Path, *, changed: bool = False, slug: str = "synthetic-rag-book"):
    root.mkdir(parents=True)
    manifest = {
        "slug": slug,
        "publisher": "Synthetic Learning Press",
        "series": "Tiny English",
        "grade": 3,
        "semester": 1,
        "title": "Synthetic RAG Book",
        "version": "test-1",
        "content_file": "content.jsonl",
    }
    records = [
        {
            "unit_no": 1,
            "unit_title": "Toy Friends",
            "lesson": "Lesson 1",
            "page": 4,
            "text": "Milo is a small blue bear. Milo likes red apples."
            + (" Milo has a green hat." if changed else ""),
        },
        {
            "unit_no": 2,
            "unit_title": "Bird Songs",
            "lesson": "Lesson 1",
            "page": 12,
            "text": "Pip is a yellow bird. Pip sings every morning.",
        },
    ]
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (root / "content.jsonl").write_text(
        "\n".join(json.dumps(item) for item in records) + "\n", encoding="utf-8"
    )
    return load_textbook_source(root)
