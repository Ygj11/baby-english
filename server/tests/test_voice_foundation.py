from importlib import import_module
from importlib.metadata import version

import pytest
from pipecat.pipeline.pipeline import Pipeline

from server.app.voice.realtime import create_realtime_pipeline
from server.app.voice.settings import load_voice_settings


def test_pipecat_is_installed() -> None:
    assert import_module("pipecat") is not None
    assert version("pipecat-ai")


def test_voice_package_loads() -> None:
    assert import_module("server.app.voice") is not None


def test_voice_settings_load_without_provider_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for variable in (
        "STT_PROVIDER",
        "STT_API_KEY",
        "LLM_PROVIDER",
        "LLM_API_KEY",
        "TTS_PROVIDER",
        "TTS_API_KEY",
    ):
        monkeypatch.delenv(variable, raising=False)

    settings = load_voice_settings()

    assert settings.stt_provider is None
    assert settings.llm_provider is None
    assert settings.tts_provider is None


def test_realtime_boundary_uses_pipecat_core_pipeline() -> None:
    pipeline = create_realtime_pipeline([])

    assert isinstance(pipeline, Pipeline)
