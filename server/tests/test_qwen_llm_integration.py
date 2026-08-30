import os

import pytest

from server.app.tutor.llm import FakeLLM, QwenLLM, create_llm
from server.app.tutor.schemas import StudentProfile
from server.app.tutor.service import TutorService


@pytest.mark.real_provider
@pytest.mark.asyncio
async def test_qwen_real_provider_returns_nonfake_child_tutor_reply() -> None:
    if os.getenv("RUN_REAL_PROVIDER_TESTS") != "1":
        pytest.skip("Set RUN_REAL_PROVIDER_TESTS=1 for real provider integration.")

    llm = create_llm("qwen")
    assert isinstance(llm, QwenLLM)
    tutor = TutorService(llm=llm)

    reply = await tutor.reply(
        "苹果英文怎么说？",
        StudentProfile(age=8, grade=3, english_level="beginner"),
    )

    assert reply.strip()
    assert reply != FakeLLM().fixed_reply
