"""Environment-backed settings for future voice integrations."""

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VoiceSettings:
    """Optional provider selections without provider credentials or defaults."""

    stt_provider: str | None = None
    llm_provider: str | None = None
    tts_provider: str | None = None


def load_voice_settings() -> VoiceSettings:
    """Load optional provider names from the environment."""
    return VoiceSettings(
        stt_provider=os.getenv("STT_PROVIDER") or None,
        llm_provider=os.getenv("LLM_PROVIDER") or None,
        tts_provider=os.getenv("TTS_PROVIDER") or None,
    )
