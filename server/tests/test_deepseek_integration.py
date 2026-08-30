import os

import pytest

from server.app.tutor.llm import OpenAICompatibleLLM, create_llm
from server.app.tutor.schemas import StudentProfile
from server.app.tutor.service import TutorService


@pytest.mark.real_provider
@pytest.mark.asyncio
async def test_deepseek_real_provider_returns_nonempty_child_tutor_reply() -> None:
    if os.getenv("RUN_DEEPSEEK_PROVIDER_TESTS") != "1":
        pytest.skip("Set RUN_DEEPSEEK_PROVIDER_TESTS=1 for DeepSeek integration.")

    llm = create_llm("openai_compatible")
    assert isinstance(llm, OpenAICompatibleLLM)
    tutor = TutorService(llm=llm)

    reply = await tutor.reply(
        "苹果英文怎么说？",
        StudentProfile(age=8, grade=3, english_level="beginner"),
    )

    assert reply.strip()
