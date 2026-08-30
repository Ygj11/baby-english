import os
from time import perf_counter

import pytest

from server.app.voice.tts import MiniMaxTTS, create_tts


@pytest.mark.real_provider
@pytest.mark.asyncio
async def test_minimax_real_provider_returns_nonempty_mp3() -> None:
    if os.getenv("RUN_REAL_PROVIDER_TESTS") != "1":
        pytest.skip("Set RUN_REAL_PROVIDER_TESTS=1 for real provider integration.")

    tts = create_tts("minimax")
    assert isinstance(tts, MiniMaxTTS)

    started = perf_counter()
    audio = await tts.synthesize("Apple. Repeat after me: apple.")
    latency_ms = round((perf_counter() - started) * 1000)

    assert audio.data
    assert audio.content_type == "audio/mpeg"
    assert audio.extension == ".mp3"
    assert latency_ms > 0
