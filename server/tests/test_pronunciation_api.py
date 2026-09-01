import logging
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select

import server.app.voice.audio as audio_module
from server.app.api.pronunciation import get_pronunciation_gateway
from server.app.main import app
from server.app.persistence.database import SessionFactory
from server.app.pronunciation.domain import (
    PronunciationIssue,
    PronunciationResult,
    WordPronunciationScore,
)
from server.app.pronunciation.gateway import PronunciationError
from server.app.pronunciation.model import PronunciationAttemptRecord


def client_headers(label: str) -> dict[str, str]:
    return {"X-Client-Id": f"test_ise_{label}_{uuid4().hex}"}


NORMAL_RESULT = PronunciationResult(
    overall_score=86.0,
    accuracy_score=82.0,
    fluency_score=91.0,
    completeness_score=100.0,
    standard_score=84.0,
    rejected=False,
    words=(
        WordPronunciationScore(
            word="banana",
            score=82.0,
            issues=(PronunciationIssue(kind="omitted", unit="n"),),
        ),
    ),
)


class RecordingGateway:
    def __init__(self, result: PronunciationResult = NORMAL_RESULT) -> None:
        self.result = result
        self.calls = 0
        self.audio_path: Path | None = None
        self.reference_text = ""
        self.category = ""

    async def evaluate(self, *, reference_text, audio_path, category):
        self.calls += 1
        self.audio_path = audio_path
        assert audio_path.exists()
        self.reference_text = reference_text
        self.category = category
        return self.result


class FailingGateway(RecordingGateway):
    async def evaluate(self, *, reference_text, audio_path, category):
        self.calls += 1
        self.audio_path = audio_path
        raise PronunciationError("provider raw XML <secret> and auth URL")


async def put_profile(client: httpx.AsyncClient, headers: dict[str, str]) -> None:
    response = await client.put(
        "/api/student/profile",
        headers=headers,
        json={"age": 8, "grade": 3, "english_level": "beginner"},
    )
    assert response.status_code == 200


async def post_evaluation(
    gateway,
    *,
    headers: dict[str, str],
    content: bytes = b"mock mp3 audio",
    reference_text: str = "banana",
    filename: str = "reading.mp3",
    content_type: str = "audio/mpeg",
    setup_profile: bool = True,
) -> httpx.Response:
    app.dependency_overrides[get_pronunciation_gateway] = lambda: gateway
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            if setup_profile:
                await put_profile(client, headers)
            return await client.post(
                "/api/pronunciation/evaluate",
                headers=headers,
                data={"reference_text": reference_text},
                files={"file": (filename, content, content_type)},
            )
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_pronunciation_api_success_persists_normalized_attempt_and_cleans_audio() -> None:
    gateway = RecordingGateway()
    headers = client_headers("success")
    response = await post_evaluation(gateway, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "attempt_id": body["attempt_id"],
        "reference_text": "banana",
        "overall_score": 86.0,
        "accuracy_score": 82.0,
        "fluency_score": 91.0,
        "completeness_score": 100.0,
        "standard_score": 84.0,
        "rejected": False,
        "words": [{"word": "banana", "score": 82.0}],
        "feedback": "很棒！读得很清楚，再读一次巩固一下。",
    }
    assert gateway.reference_text == "banana"
    assert gateway.category == "read_word"
    assert gateway.audio_path is not None and not gateway.audio_path.exists()
    assert "xml" not in response.text.lower()
    assert "auth" not in response.text.lower()

    async with SessionFactory() as session:
        record = await session.get(PronunciationAttemptRecord, body["attempt_id"])
    assert record is not None
    assert record.client_id == headers["X-Client-Id"]
    assert record.reference_text == "banana"
    assert record.category == "read_word"
    assert record.detail_json == (
        '[{"word":"banana","score":82.0,'
        '"issues":[{"kind":"omitted","unit":"n"}]}]'
    )
    assert "<" not in record.detail_json
    assert not hasattr(record, "audio")


@pytest.mark.asyncio
async def test_rejected_attempt_is_explicit_and_persisted() -> None:
    rejected = PronunciationResult(
        overall_score=12.0,
        accuracy_score=10.0,
        fluency_score=15.0,
        completeness_score=0.0,
        standard_score=None,
        rejected=True,
    )
    headers = client_headers("rejected")
    response = await post_evaluation(RecordingGateway(rejected), headers=headers)

    assert response.status_code == 200
    assert response.json()["rejected"] is True
    assert "重新读一次" in response.json()["feedback"]
    async with SessionFactory() as session:
        record = await session.get(
            PronunciationAttemptRecord, response.json()["attempt_id"]
        )
    assert record is not None and record.rejected is True


@pytest.mark.asyncio
async def test_missing_profile_short_circuits_before_ise() -> None:
    gateway = RecordingGateway()
    response = await post_evaluation(
        gateway,
        headers=client_headers("missing_profile"),
        setup_profile=False,
    )
    assert response.status_code == 409
    assert gateway.calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "reference",
    ["", "香蕉", "word " * 13, "x" * 201, "read 123"],
)
async def test_invalid_reference_does_not_call_ise(reference: str) -> None:
    gateway = RecordingGateway()
    response = await post_evaluation(
        gateway,
        headers=client_headers("invalid_reference"),
        reference_text=reference,
    )
    assert response.status_code == 400
    assert gateway.calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("content", "filename", "content_type", "expected"),
    [
        (b"", "reading.mp3", "audio/mpeg", 400),
        (b"wave", "reading.wav", "audio/wav", 400),
    ],
)
async def test_invalid_audio_uses_existing_validation_semantics(
    content: bytes,
    filename: str,
    content_type: str,
    expected: int,
) -> None:
    gateway = RecordingGateway()
    response = await post_evaluation(
        gateway,
        headers=client_headers("invalid_audio"),
        content=content,
        filename=filename,
        content_type=content_type,
    )
    assert response.status_code == expected
    assert gateway.calls == 0


@pytest.mark.asyncio
async def test_oversize_audio_returns_413_without_ise(monkeypatch) -> None:
    monkeypatch.setattr(audio_module, "MAX_AUDIO_BYTES", 4)
    gateway = RecordingGateway()
    response = await post_evaluation(
        gateway,
        headers=client_headers("oversize"),
        content=b"12345",
    )
    assert response.status_code == 413
    assert gateway.calls == 0


@pytest.mark.asyncio
async def test_provider_error_is_safe_and_temp_audio_is_deleted(caplog) -> None:
    caplog.set_level(logging.WARNING, logger="uvicorn.error.baby_english.pronunciation")
    gateway = FailingGateway()
    response = await post_evaluation(gateway, headers=client_headers("failure"))

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Pronunciation practice is temporarily unavailable."
    }
    assert "provider raw" not in response.text
    assert "provider raw" not in caplog.text
    assert "stage=ise" in caplog.text
    assert gateway.audio_path is not None and not gateway.audio_path.exists()


@pytest.mark.asyncio
async def test_attempt_rows_remain_owned_by_each_client() -> None:
    headers_a = client_headers("owner_a")
    headers_b = client_headers("owner_b")
    first = await post_evaluation(RecordingGateway(), headers=headers_a)
    second = await post_evaluation(RecordingGateway(), headers=headers_b)

    async with SessionFactory() as session:
        records = list(
            (
                await session.scalars(
                    select(PronunciationAttemptRecord).where(
                        PronunciationAttemptRecord.id.in_(
                            [first.json()["attempt_id"], second.json()["attempt_id"]]
                        )
                    )
                )
            )
        )
    assert {record.client_id for record in records} == {
        headers_a["X-Client-Id"],
        headers_b["X-Client-Id"],
    }
