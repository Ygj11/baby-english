import json
import logging
import os
import re
from pathlib import Path
from statistics import median

import httpx
import pytest

from server.app.api.voice import media_store
from server.app.main import app
from server.app.tutor.llm import FakeLLM
from server.app.voice.stt import FakeSTT

LATENCY_PATTERN = re.compile(
    r"stt_ms=(?P<stt>\d+) llm_ms=(?P<llm>\d+) "
    r"tts_ms=(?P<tts>\d+) total_ms=(?P<total>\d+)"
)


@pytest.mark.real_provider
@pytest.mark.asyncio
async def test_real_qwen_text_and_five_voice_turns(
    caplog: pytest.LogCaptureFixture,
) -> None:
    if os.getenv("RUN_REAL_PROVIDER_TESTS") != "1":
        pytest.skip("Set RUN_REAL_PROVIDER_TESTS=1 for real provider integration.")

    audio_value = os.getenv("REAL_STT_AUDIO_PATH", "")
    if not audio_value:
        pytest.skip("Set REAL_STT_AUDIO_PATH to a local WAV or MP3 file.")
    audio_path = Path(audio_value)
    if not audio_path.is_file():
        pytest.skip("REAL_STT_AUDIO_PATH does not exist.")

    caplog.set_level(logging.INFO, logger="uvicorn.error.baby_english.voice")
    transport = httpx.ASGITransport(app=app)
    latency_rows: list[dict[str, int]] = []
    first_voice_response = None
    client_headers = {"X-Client-Id": "real_qwen_e2e_client_00000001"}

    try:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
            timeout=240,
        ) as client:
            profile_response = await client.put(
                "/api/student/profile",
                headers=client_headers,
                json={"age": 8, "grade": 3, "english_level": "beginner"},
            )
            assert profile_response.status_code == 200
            chat_response = await client.post(
                "/api/tutor/chat",
                json={
                    "message": "苹果英文怎么说？",
                    "context": {"mode": "chat"},
                },
                headers=client_headers,
            )
            assert chat_response.status_code == 200
            chat_data = chat_response.json()
            assert chat_data["reply"].strip()
            assert chat_data["reply"] != FakeLLM().fixed_reply
            assert chat_data["repeat_text"]
            assert chat_data["suggested_actions"] == ["repeat", "explain_zh"]

            for _ in range(5):
                response = await client.post(
                    "/api/voice/turn",
                    headers=client_headers,
                    files={
                        "file": (
                            audio_path.name,
                            audio_path.read_bytes(),
                            "audio/wav" if audio_path.suffix.lower() == ".wav" else "audio/mpeg",
                        )
                    },
                )
                assert response.status_code == 200
                voice_data = response.json()
                if first_voice_response is None:
                    first_voice_response = voice_data
                assert voice_data["transcript"].strip()
                assert voice_data["transcript"] != FakeSTT().fixed_text
                assert voice_data["reply"].strip()
                assert voice_data["reply"] != FakeLLM().fixed_reply
                assert voice_data["repeat_text"]
                assert voice_data["audio_url"].startswith("/api/voice/media/")
                assert "base64" not in response.text.lower()
                assert "aliyuncs.com" not in response.text
                assert voice_data["suggested_actions"] == [
                    "listen",
                    "repeat",
                    "explain_zh",
                ]

                media_response = await client.get(voice_data["audio_url"])
                assert media_response.status_code == 200
                assert media_response.headers["content-type"].startswith("audio/mpeg")
                assert len(media_response.content) > 128

                latency_record = next(
                    record
                    for record in reversed(caplog.records)
                    if record.getMessage().startswith("voice_turn_latency ")
                )
                match = LATENCY_PATTERN.search(latency_record.getMessage())
                assert match is not None
                latency_rows.append(
                    {name: int(value) for name, value in match.groupdict().items()}
                )
    finally:
        media_store.cleanup()

    assert first_voice_response is not None
    summary = {
        stage: {
            "min": min(row[stage] for row in latency_rows),
            "median": median(row[stage] for row in latency_rows),
            "max": max(row[stage] for row in latency_rows),
        }
        for stage in ("stt", "llm", "tts", "total")
    }
    print(
        "QWEN_E2E_RESULT="
        + json.dumps(
            {
                "chat_status": 200,
                "voice_status": 200,
                "transcript": first_voice_response["transcript"],
                "reply_nonempty": bool(first_voice_response["reply"].strip()),
                "media_content_type": "audio/mpeg",
                "turns": latency_rows,
                "summary": summary,
            },
            ensure_ascii=False,
        )
    )
