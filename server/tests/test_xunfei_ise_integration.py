import json
import os
from pathlib import Path

import pytest

from server.app.pronunciation.gateway import create_pronunciation_gateway
from server.app.pronunciation.reference import (
    InvalidReferenceTextError,
    choose_category,
    normalize_reference_text,
)


@pytest.mark.real_provider
@pytest.mark.asyncio
async def test_xunfei_ise_real_provider_returns_normalized_result() -> None:
    if os.getenv("RUN_REAL_PROVIDER_TESTS") != "1":
        pytest.skip("Set RUN_REAL_PROVIDER_TESTS=1 for real provider integration.")
    required = ("XFYUN_APP_ID", "XFYUN_API_KEY", "XFYUN_API_SECRET")
    if any(not os.getenv(name, "").strip() for name in required):
        pytest.skip("Configure XFYUN_APP_ID/XFYUN_API_KEY/XFYUN_API_SECRET.")

    audio_value = os.getenv("REAL_ISE_AUDIO_PATH", "")
    reference_value = os.getenv("REAL_ISE_REFERENCE_TEXT", "")
    audio_path = Path(audio_value)
    if not audio_path.is_file() or audio_path.suffix.lower() != ".mp3":
        pytest.skip("REAL_ISE_AUDIO_PATH must be an existing MP3 outside the repo.")
    repository_root = Path(__file__).resolve().parents[2]
    if audio_path.resolve().is_relative_to(repository_root):
        pytest.skip("REAL_ISE_AUDIO_PATH must point outside the repository.")
    try:
        reference = normalize_reference_text(reference_value)
    except InvalidReferenceTextError:
        pytest.skip("REAL_ISE_REFERENCE_TEXT must be a valid English target.")
    original_size = audio_path.stat().st_size

    result = await create_pronunciation_gateway("xunfei").evaluate(
        reference_text=reference,
        audio_path=audio_path,
        category=choose_category(reference),
    )

    for score in (
        result.overall_score,
        result.accuracy_score,
        result.fluency_score,
        result.completeness_score,
        result.standard_score,
    ):
        assert score is None or 0 <= score <= 100
    assert audio_path.is_file()
    assert audio_path.stat().st_size == original_size
    print(
        "XUNFEI_ISE_RESULT="
        + json.dumps(
            {
                "overall_score": result.overall_score,
                "accuracy_score": result.accuracy_score,
                "fluency_score": result.fluency_score,
                "completeness_score": result.completeness_score,
                "standard_score": result.standard_score,
                "rejected": result.rejected,
                "word_count": len(result.words),
            }
        )
    )
