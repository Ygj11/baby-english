from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

import server.app.api.textbooks as textbook_api
from server.app.main import app
from server.app.persistence.database import SessionFactory
from server.app.textbook.domain import RetrievedTextbookChunk, TextbookConfigurationError, TextbookIndexError
from server.app.textbook.repository import SQLAlchemyTextbookRepository
from server.app.tutor.llm import LLMError
from server.tests.textbook_helpers import synthetic_source


PROFILE = {"age": 8, "grade": 3, "english_level": "beginner"}


def headers(label: str) -> dict[str, str]:
    return {"X-Client-Id": f"textbook_{label}_{uuid4().hex}"[:64]}


async def setup_profile(client: httpx.AsyncClient, owner: dict[str, str]) -> None:
    response = await client.put("/api/student/profile", headers=owner, json=PROFILE)
    assert response.status_code == 200


async def add_book(tmp_path: Path):
    slug = f"api-book-{uuid4().hex}"
    source = synthetic_source(tmp_path / slug, slug=slug)
    async with SessionFactory() as session:
        return await SQLAlchemyTextbookRepository(session).upsert_ingested(
            source,
            embedding_model="fake-textbook-embedding",
            embedding_dimensions=1024,
            index_schema_version=1,
            indexed_at=datetime.now(UTC),
        )


class FixedRetriever:
    def __init__(self, chunks=(), error: Exception | None = None):
        self.chunks = chunks
        self.error = error
        self.calls = []

    async def retrieve(self, textbook, *, question, unit_no):
        self.calls.append((textbook, question, unit_no))
        if self.error:
            raise self.error
        return self.chunks


class FixedLLM:
    def __init__(self, error: Exception | None = None):
        self.error = error
        self.calls = []

    async def generate(self, *, system_prompt, message, history=()):
        self.calls.append((system_prompt, message))
        if self.error:
            raise self.error
        return "Milo 是一只蓝色小熊。"


CHUNK = RetrievedTextbookChunk(
    text="Milo is a small blue bear.",
    score=0.9,
    unit_no=1,
    unit_title="Toy Friends",
    lesson="Lesson 1",
    page=4,
    source_record=1,
)


@pytest.mark.asyncio
async def test_catalogue_requires_profile_has_safe_shape_and_selection_is_persisted(
    tmp_path: Path,
) -> None:
    book = await add_book(tmp_path)
    owner = headers("catalogue")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        missing_profile = await client.get("/api/textbooks", headers=owner)
        await setup_profile(client, owner)
        catalogue = await client.get("/api/textbooks", headers=owner)
        units = await client.get(f"/api/textbooks/{book.id}/units", headers=owner)
        empty_current = await client.get("/api/textbooks/current", headers=owner)
        selected = await client.put(
            "/api/textbooks/current",
            headers=owner,
            json={"textbook_id": book.id, "current_unit_no": 1},
        )
        current = await client.get("/api/textbooks/current", headers=owner)
    assert missing_profile.status_code == 409
    assert catalogue.status_code == 200
    public_book = next(item for item in catalogue.json() if item["id"] == book.id)
    assert set(public_book) == {
        "id", "title", "publisher", "series", "grade", "semester", "version", "selected"
    }
    assert public_book["selected"] is False
    assert "path" not in catalogue.text.lower() and "vector" not in catalogue.text.lower()
    assert units.json() == [
        {"unit_no": 1, "title": "Toy Friends"},
        {"unit_no": 2, "title": "Bird Songs"},
    ]
    assert empty_current.json() == {"textbook": None, "current_unit_no": None, "units": []}
    assert selected.status_code == 200 and selected.json()["current_unit_no"] == 1
    assert current.json()["textbook"]["id"] == book.id
    assert current.json()["current_unit_no"] == 1


@pytest.mark.asyncio
async def test_selection_validation_and_client_isolation(tmp_path: Path) -> None:
    book = await add_book(tmp_path)
    owner_a, owner_b = headers("owner_a"), headers("owner_b")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await setup_profile(client, owner_a)
        await setup_profile(client, owner_b)
        ok = await client.put(
            "/api/textbooks/current", headers=owner_a,
            json={"textbook_id": book.id, "current_unit_no": 2},
        )
        invalid = await client.put(
            "/api/textbooks/current", headers=owner_b,
            json={"textbook_id": book.id, "current_unit_no": 999},
        )
        current_a = await client.get("/api/textbooks/current", headers=owner_a)
        current_b = await client.get("/api/textbooks/current", headers=owner_b)
        unknown = await client.get("/api/textbooks/99999999/units", headers=owner_a)
    assert ok.status_code == 200
    assert invalid.status_code == 404
    assert current_a.json()["current_unit_no"] == 2
    assert current_b.json()["textbook"] is None
    assert unknown.status_code == 404


@pytest.mark.asyncio
async def test_ask_requires_profile_and_selection_before_providers(tmp_path: Path, monkeypatch) -> None:
    owner = headers("ask_preconditions")
    calls = []
    monkeypatch.setattr(textbook_api, "create_textbook_embedding", lambda: calls.append("embedding"))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        no_profile = await client.post("/api/textbooks/ask", headers=owner, json={"question": "Hi"})
        await setup_profile(client, owner)
        no_selection = await client.post("/api/textbooks/ask", headers=owner, json={"question": "Hi"})
    assert no_profile.status_code == 409
    assert no_selection.status_code == 409
    assert calls == []


@pytest.mark.asyncio
async def test_successful_ask_returns_answer_and_compact_sources(tmp_path: Path, monkeypatch) -> None:
    book = await add_book(tmp_path)
    owner = headers("ask_success")
    retriever, llm = FixedRetriever((CHUNK, CHUNK)), FixedLLM()
    monkeypatch.setattr(textbook_api, "create_textbook_embedding", lambda: object())
    monkeypatch.setattr(textbook_api, "TextbookRetriever", lambda embedding: retriever)
    monkeypatch.setattr(textbook_api, "create_llm", lambda: llm)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await setup_profile(client, owner)
        await client.put(
            "/api/textbooks/current", headers=owner,
            json={"textbook_id": book.id, "current_unit_no": 1},
        )
        response = await client.post(
            "/api/textbooks/ask", headers=owner, json={"question": "Milo 是什么颜色？"}
        )
    assert response.status_code == 200
    assert response.json() == {
        "answer": "Milo 是一只蓝色小熊。",
        "found": True,
        "sources": [{"unit_no": 1, "unit_title": "Toy Friends", "lesson": "Lesson 1", "page": 4}],
    }
    assert "Milo is a small blue bear" not in response.text
    assert retriever.calls[0][2] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["embedding", "index", "llm"])
async def test_provider_and_index_failures_are_safe_503(
    tmp_path: Path, monkeypatch, failure: str, caplog
) -> None:
    book = await add_book(tmp_path)
    owner = headers(f"failure_{failure}")
    secret = "raw-provider-secret-and-source-path"
    if failure == "embedding":
        def fail_embedding():
            raise TextbookConfigurationError(secret)
        monkeypatch.setattr(textbook_api, "create_textbook_embedding", fail_embedding)
    else:
        retriever = FixedRetriever(
            error=TextbookIndexError(secret) if failure == "index" else None,
            chunks=(CHUNK,),
        )
        monkeypatch.setattr(textbook_api, "create_textbook_embedding", lambda: object())
        monkeypatch.setattr(textbook_api, "TextbookRetriever", lambda embedding: retriever)
        monkeypatch.setattr(
            textbook_api,
            "create_llm",
            lambda: FixedLLM(LLMError(secret) if failure == "llm" else None),
        )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await setup_profile(client, owner)
        await client.put(
            "/api/textbooks/current", headers=owner,
            json={"textbook_id": book.id, "current_unit_no": 1},
        )
        response = await client.post(
            "/api/textbooks/ask", headers=owner, json={"question": "What is Milo?"}
        )
    assert response.status_code == 503
    assert response.json() == {"detail": "Textbook learning is temporarily unavailable."}
    assert secret not in response.text
    assert secret not in caplog.text
