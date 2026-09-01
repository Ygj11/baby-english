"""iFlytek streaming ISE WebSocket adapter for 16 kHz mono MP3."""

import asyncio
import base64
import binascii
from collections.abc import AsyncIterator, Callable
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import format_datetime
import hashlib
import hmac
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from websockets.asyncio.client import connect as websocket_connect
from websockets.exceptions import WebSocketException

from server.app.pronunciation.domain import EvaluationCategory, PronunciationResult
from server.app.pronunciation.gateway import PronunciationError
from server.app.pronunciation.parser import ISEParseError, parse_ise_result
from server.app.pronunciation.reference import build_test_paper


ISE_HOST = "ise-api.xfyun.cn"
ISE_PATH = "/v2/open-ise"
ISE_ENDPOINT = f"wss://{ISE_HOST}{ISE_PATH}"
FRAME_BYTES = 1280
FRAME_INTERVAL_SECONDS = 0.04
MAX_PROVIDER_FRAME_BYTES = 19_200


@dataclass(frozen=True, slots=True)
class XunfeiISEConfig:
    app_id: str = field(repr=False)
    api_key: str = field(repr=False)
    api_secret: str = field(repr=False)
    timeout: float = 60.0


@dataclass(slots=True)
class XunfeiISEPronunciationGateway:
    config: XunfeiISEConfig = field(repr=False)
    connector: Callable[..., Any] = field(default=websocket_connect, repr=False)

    async def evaluate(
        self,
        *,
        reference_text: str,
        audio_path: Path,
        category: EvaluationCategory,
    ) -> PronunciationResult:
        if audio_path.suffix.lower() != ".mp3":
            raise PronunciationError("ISE requires a validated MP3 upload.")
        try:
            audio = audio_path.read_bytes()
        except OSError as error:
            raise PronunciationError("Could not read pronunciation audio.") from error
        if not audio:
            raise PronunciationError("Pronunciation audio is empty.")

        auth_url = build_xunfei_auth_url(
            api_key=self.config.api_key,
            api_secret=self.config.api_secret,
        )
        try:
            async with asyncio.timeout(self.config.timeout):
                async with self.connector(auth_url, max_size=2 * 1024 * 1024) as socket:
                    await socket.send(
                        json.dumps(
                            build_ssb_frame(
                                app_id=self.config.app_id,
                                reference_text=reference_text,
                                category=category,
                            )
                        )
                    )
                    receiver = asyncio.create_task(_receive_final_xml(socket))
                    try:
                        await _send_audio(socket, audio, receiver)
                        xml_payload = await receiver
                    finally:
                        if not receiver.done():
                            receiver.cancel()
                            with suppress(asyncio.CancelledError):
                                await receiver
        except PronunciationError:
            raise
        except (TimeoutError, WebSocketException, OSError, json.JSONDecodeError) as error:
            raise PronunciationError("The pronunciation provider request failed.") from error

        try:
            # ise_unite=1 requests percentage-oriented scores. Supplying that
            # request context prevents a genuinely low score (for example 4%)
            # from being mistaken for a legacy 0-5 result.
            return parse_ise_result(xml_payload, percentage_scores=True)
        except ISEParseError as error:
            raise PronunciationError("The pronunciation provider returned an invalid result.") from error


def build_xunfei_auth_url(
    *,
    api_key: str,
    api_secret: str,
    now: datetime | None = None,
) -> str:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    date = format_datetime(current.astimezone(timezone.utc), usegmt=True)
    signature_origin = f"host: {ISE_HOST}\ndate: {date}\nGET {ISE_PATH} HTTP/1.1"
    signature = base64.b64encode(
        hmac.new(
            api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            hashlib.sha256,
        ).digest()
    ).decode("ascii")
    authorization_origin = (
        f'api_key="{api_key}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature}"'
    )
    authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode(
        "ascii"
    )
    return f"{ISE_ENDPOINT}?{urlencode({'authorization': authorization, 'date': date, 'host': ISE_HOST})}"


def build_ssb_frame(
    *,
    app_id: str,
    reference_text: str,
    category: EvaluationCategory,
) -> dict[str, Any]:
    return {
        "common": {"app_id": app_id},
        "business": {
            "sub": "ise",
            "ent": "en_vip",
            "category": category,
            "cmd": "ssb",
            "auf": "audio/L16;rate=16000",
            "aue": "lame",
            "text": build_test_paper(reference_text, category),
            "tte": "utf-8",
            "ttp_skip": True,
            "rstcd": "utf8",
            "rst": "entirety",
            "ise_unite": "1",
            "extra_ability": "multi_dimension;syll_phone_err_msg",
        },
        "data": {"status": 0, "data": ""},
    }


def iter_audio_frames(audio: bytes) -> AsyncIterator[dict[str, Any]]:
    async def frames() -> AsyncIterator[dict[str, Any]]:
        first = True
        for offset in range(0, len(audio), FRAME_BYTES):
            chunk = audio[offset : offset + FRAME_BYTES]
            if len(chunk) > MAX_PROVIDER_FRAME_BYTES:
                raise PronunciationError("Pronunciation audio frame is too large.")
            yield {
                "business": {"cmd": "auw", "aus": 1 if first else 2, "aue": "lame"},
                "data": {
                    "status": 1,
                    "data": base64.b64encode(chunk).decode("ascii"),
                },
            }
            first = False
        yield {
            "business": {"cmd": "auw", "aus": 4, "aue": "lame"},
            "data": {"status": 2, "data": ""},
        }

    return frames()


async def _send_audio(socket: Any, audio: bytes, receiver: asyncio.Task[str]) -> None:
    async for frame in iter_audio_frames(audio):
        if receiver.done():
            await receiver
            return
        await socket.send(json.dumps(frame))
        if frame["data"]["status"] != 2:
            await asyncio.sleep(FRAME_INTERVAL_SECONDS)


async def _receive_final_xml(socket: Any) -> str:
    final_xml: str | None = None
    received_final_status = False
    async for message in socket:
        response = json.loads(message)
        if response.get("code") != 0:
            raise PronunciationError("The pronunciation provider rejected the request.")
        data = response.get("data")
        if not isinstance(data, dict):
            continue
        encoded = data.get("data")
        if encoded:
            try:
                final_xml = base64.b64decode(encoded, validate=True).decode("utf-8")
            except (binascii.Error, ValueError, UnicodeDecodeError) as error:
                raise PronunciationError(
                    "The pronunciation provider returned invalid result data."
                ) from error
        if data.get("status") == 2:
            received_final_status = True
            break
    if not final_xml or not received_final_status:
        raise PronunciationError("The pronunciation provider returned no result.")
    return final_xml
