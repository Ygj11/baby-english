import os
from pathlib import Path
from time import perf_counter

import pytest

from server.app.voice.stt import QwenAudioSTT, create_stt


@pytest.mark.real_provider
@pytest.mark.asyncio
async def test_qwen_audio_real_provider_transcribes_local_audio() -> None:
    if os.getenv("RUN_REAL_PROVIDER_TESTS") != "1":
        pytest.skip("Set RUN_REAL_PROVIDER_TESTS=1 for real provider integration.")

    audio_value = os.getenv("REAL_STT_AUDIO_PATH", "")
    if not audio_value:
        pytest.skip("Set REAL_STT_AUDIO_PATH to a local WAV or MP3 file.")
    audio_path = Path(audio_value)
    if not audio_path.is_file():
        pytest.skip("REAL_STT_AUDIO_PATH does not exist.")
    stt = create_stt("qwen_audio")
    assert isinstance(stt, QwenAudioSTT)

    started = perf_counter()
    transcript = await stt.transcribe(audio_path)
    latency_ms = round((perf_counter() - started) * 1000)

    assert transcript.text.strip()
    assert transcript.duration_ms >= 0
    assert latency_ms > 0
