import os
from time import perf_counter

import pytest

from server.app.voice.media import TemporaryMediaStore
from server.app.voice.tts import QwenAudioTTS, create_tts


@pytest.mark.real_provider
@pytest.mark.asyncio
async def test_qwen_tts_real_provider_returns_storable_mp3(tmp_path) -> None:
    if os.getenv("RUN_REAL_PROVIDER_TESTS") != "1":
        pytest.skip("Set RUN_REAL_PROVIDER_TESTS=1 for real provider integration.")

    tts = create_tts("qwen_audio")
    assert isinstance(tts, QwenAudioTTS)

    started = perf_counter()
    audio = await tts.synthesize("Banana. Repeat after me: banana.")
    latency_ms = round((perf_counter() - started) * 1000)
    store = TemporaryMediaStore(base_dir=tmp_path)
    media_id = store.save(audio)
    asset = store.get(media_id)

    assert len(audio.data) > 128
    assert audio.content_type == "audio/mpeg"
    assert audio.extension == ".mp3"
    assert asset is not None
    assert asset.path.read_bytes() == audio.data
    assert latency_ms > 0
