import pytest

from server.app.tutor.service import TutorService
from server.app.tutor.schemas import StudentProfile


class RecordingFakeLLM:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.system_prompt = ""

    async def generate(self, *, system_prompt: str, message: str) -> str:
        self.system_prompt = system_prompt
        return self.reply


@pytest.mark.asyncio
async def test_beginner_apple_golden_case() -> None:
    llm = RecordingFakeLLM("Apple 🍎. Repeat after me: apple.")
    service = TutorService(llm=llm)

    reply = await service.reply(
        "苹果英文怎么说？",
        StudentProfile(age=8, grade=3, english_level="beginner"),
    )

    prompt = llm.system_prompt.lower()
    assert "apple" in reply.lower()
    assert "repeat" in reply.lower()
    assert len(reply.split()) <= 8
    assert "short" in prompt
    assert "one main learning point" in prompt
    assert "no more than 3 new words" in prompt
    assert "brief chinese support" in prompt
    assert "repeat" in prompt
    assert "avoid complex grammar terminology" in prompt


@pytest.mark.asyncio
async def test_elementary_plural_golden_case() -> None:
    llm = RecordingFakeLLM(
        "Apple means one. Apples means more than one. Adding -s makes it plural."
    )
    service = TutorService(llm=llm)

    reply = await service.reply(
        "apple和apples有什么区别？",
        StudentProfile(age=11, grade=5, english_level="elementary"),
    )

    prompt = llm.system_prompt.lower()
    assert "plural" in reply.lower()
    assert "mostly english" in prompt
    assert "simple grammar" in prompt
    assert "singular and plural" in prompt
    assert "keep grammar explanations short" in prompt
