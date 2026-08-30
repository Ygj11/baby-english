import httpx
import pytest

from server.app.api.tutor import get_tutor_service
from server.app.main import app
from server.app.tutor.llm import FakeLLM, LLMError, create_llm
from server.app.tutor.service import TutorService

CHAT_REQUEST = {
    "message": "苹果英文怎么说？",
    "student": {
        "age": 8,
        "grade": 3,
        "english_level": "beginner",
    },
    "context": {"mode": "chat"},
}


async def post_chat(
    service: TutorService,
    request: dict | None = None,
) -> httpx.Response:
    app.dependency_overrides[get_tutor_service] = lambda: service
    transport = httpx.ASGITransport(app=app)

    try:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            return await client.post(
                "/api/tutor/chat",
                json=request if request is not None else CHAT_REQUEST,
            )
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_fake_llm_has_fixed_reply() -> None:
    llm = FakeLLM(fixed_reply="Fixed tutor reply.")

    reply = await llm.generate(system_prompt="test", message="hello")

    assert reply == "Fixed tutor reply."


def test_no_provider_configuration_uses_fake_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    assert isinstance(create_llm(), FakeLLM)


@pytest.mark.asyncio
async def test_chat_contract() -> None:
    response = await post_chat(
        TutorService(llm=FakeLLM("Apple 🍎. Repeat after me: apple."))
    )

    assert response.status_code == 200
    assert response.json() == {
        "reply": "Apple 🍎. Repeat after me: apple.",
        "language": "mixed",
        "suggested_actions": ["repeat", "explain_zh"],
    }
    assert "listen" not in response.json()["suggested_actions"]


class FailingLLM:
    async def generate(self, *, system_prompt: str, message: str) -> str:
        raise LLMError("provider raw error")


class CountingLLM:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, *, system_prompt: str, message: str) -> str:
        self.calls += 1
        return "This should not be called."


@pytest.mark.asyncio
async def test_provider_failure_returns_safe_error() -> None:
    response = await post_chat(TutorService(llm=FailingLLM()))

    assert response.status_code == 503
    assert response.json() == {"detail": "Tutor is temporarily unavailable."}
    assert "provider raw error" not in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize("message", ["", "   ", "x" * 2001])
async def test_invalid_message_returns_422_without_calling_llm(message: str) -> None:
    llm = CountingLLM()
    request = {
        **CHAT_REQUEST,
        "message": message,
    }

    response = await post_chat(TutorService(llm=llm), request)

    assert response.status_code == 422
    assert llm.calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value"),
    [("age", 4), ("age", 16), ("grade", 0), ("grade", 10)],
)
async def test_invalid_student_range_returns_422_without_calling_llm(
    field: str,
    value: int,
) -> None:
    llm = CountingLLM()
    request = {
        **CHAT_REQUEST,
        "student": {
            **CHAT_REQUEST["student"],
            field: value,
        },
    }

    response = await post_chat(TutorService(llm=llm), request)

    assert response.status_code == 422
    assert llm.calls == 0


@pytest.mark.asyncio
async def test_unknown_chat_mode_returns_422_without_calling_llm() -> None:
    llm = CountingLLM()
    request = {
        **CHAT_REQUEST,
        "context": {"mode": "voice"},
    }

    response = await post_chat(TutorService(llm=llm), request)

    assert response.status_code == 422
    assert llm.calls == 0
