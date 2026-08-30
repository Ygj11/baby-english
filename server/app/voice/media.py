"""Short-lived storage for synthesized voice replies."""

import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from server.app.voice.tts import SynthesizedAudio


@dataclass(frozen=True, slots=True)
class MediaAsset:
    path: Path
    content_type: str
    expires_at: float


class TemporaryMediaStore:
    def __init__(
        self,
        *,
        base_dir: Path | None = None,
        ttl_seconds: int = 300,
    ) -> None:
        self._temporary_directory = None
        if base_dir is None:
            self._temporary_directory = tempfile.TemporaryDirectory(
                prefix="baby-english-media-"
            )
            base_dir = Path(self._temporary_directory.name)
        else:
            base_dir.mkdir(parents=True, exist_ok=True)

        self._base_dir = base_dir
        self._ttl_seconds = ttl_seconds
        self._assets: dict[str, MediaAsset] = {}

    def save(self, audio: SynthesizedAudio) -> str:
        self.purge_expired()
        media_id = uuid4().hex
        path = self._base_dir / f"{media_id}{audio.extension}"
        path.write_bytes(audio.data)
        self._assets[media_id] = MediaAsset(
            path=path,
            content_type=audio.content_type,
            expires_at=time.monotonic() + self._ttl_seconds,
        )
        return media_id

    def get(self, media_id: str) -> MediaAsset | None:
        self.purge_expired()
        return self._assets.get(media_id)

    def purge_expired(self) -> None:
        now = time.monotonic()
        expired_ids = [
            media_id
            for media_id, asset in self._assets.items()
            if asset.expires_at <= now
        ]
        for media_id in expired_ids:
            self._delete(media_id)

    def cleanup(self) -> None:
        for media_id in list(self._assets):
            self._delete(media_id)

    def _delete(self, media_id: str) -> None:
        asset = self._assets.pop(media_id, None)
        if asset is not None:
            asset.path.unlink(missing_ok=True)
