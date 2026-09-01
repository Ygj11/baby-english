import base64
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from server.app.pronunciation.gateway import (
    FakePronunciationGateway,
    PronunciationConfigurationError,
    create_pronunciation_gateway,
)
from server.app.pronunciation.parser import ISEParseError, parse_ise_result
from server.app.pronunciation.reference import (
    InvalidReferenceTextError,
    build_test_paper,
    choose_category,
)
from server.app.pronunciation.xunfei import (
    XunfeiISEConfig,
    XunfeiISEPronunciationGateway,
    build_ssb_frame,
    build_xunfei_auth_url,
    iter_audio_frames,
)


PERCENTAGE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<xml_result><read_sentence lan="en"><rec_paper>
<read_sentence total_score="86.4" accuracy_score="82" fluency_score="91"
 integrity_score="100" standard_score="84" is_rejected="false">
 <sentence><word content="banana" total_score="82" werr_msg="1">
  <syll content="nana" serr_msg="1"><phone content="n" dp_message="16" /></syll>
 </word><word content="sil" total_score="99" /></sentence>
</read_sentence></rec_paper></read_sentence></xml_result>"""


def test_auth_url_uses_hmac_query_without_plaintext_secrets() -> None:
    url = build_xunfei_auth_url(
        api_key="public-key",
        api_secret="top-secret",
        now=datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc),
    )
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    authorization = base64.b64decode(query["authorization"][0]).decode()

    assert parsed.scheme == "wss"
    assert parsed.netloc == "ise-api.xfyun.cn"
    assert parsed.path == "/v2/open-ise"
    assert "public-key" not in url
    assert "top-secret" not in url
    assert 'api_key="public-key"' in authorization
    assert "top-secret" not in authorization
    assert query["host"] == ["ise-api.xfyun.cn"]


def test_xunfei_config_repr_hides_credentials() -> None:
    rendered = repr(
        XunfeiISEConfig(
            app_id="app-secret-value",
            api_key="key-secret-value",
            api_secret="api-secret-value",
        )
    )
    assert "secret-value" not in rendered


def test_word_and_sentence_paper_format_and_category() -> None:
    assert choose_category("banana") == "read_word"
    assert build_test_paper("banana", "read_word") == "\ufeff[word]\nbanana"
    assert choose_category("Can I have water, please?") == "read_sentence"
    assert build_test_paper(
        "Can I have water, please?", "read_sentence"
    ) == "\ufeff[content]\nCan I have water, please?"

    with pytest.raises(InvalidReferenceTextError):
        choose_category("香蕉 banana")


def test_ssb_selects_english_percentage_dimensions_and_mp3() -> None:
    frame = build_ssb_frame(
        app_id="app-id",
        reference_text="banana",
        category="read_word",
    )
    business = frame["business"]

    assert business["ent"] == "en_vip"
    assert business["sub"] == "ise"
    assert business["aue"] == "lame"
    assert business["auf"] == "audio/L16;rate=16000"
    assert business["rst"] == "entirety"
    assert business["ise_unite"] == "1"
    assert "multi_dimension" in business["extra_ability"]
    assert frame["data"]["status"] == 0


@pytest.mark.asyncio
async def test_audio_frame_sequence_is_first_middle_final() -> None:
    frames = [frame async for frame in iter_audio_frames(b"x" * 2600)]

    assert [frame["business"]["aus"] for frame in frames] == [1, 2, 2, 4]
    assert [frame["data"]["status"] for frame in frames] == [1, 1, 1, 2]
    assert frames[-1]["data"]["data"] == ""
    assert all(frame["business"]["aue"] == "lame" for frame in frames)


def test_parser_normalizes_percentage_scores_words_and_errors() -> None:
    result = parse_ise_result(PERCENTAGE_XML)

    assert result.overall_score == 86.4
    assert result.accuracy_score == 82.0
    assert result.fluency_score == 91.0
    assert result.completeness_score == 100.0
    assert result.standard_score == 84.0
    assert result.rejected is False
    assert [word.word for word in result.words] == ["banana"]
    assert result.words[0].score == 82.0
    assert {issue.kind for issue in result.words[0].issues} == {
        "pronunciation_variance",
        "omitted",
    }


def test_parser_tolerates_legacy_scale_and_rejected_result() -> None:
    xml = """<xml_result><read_word><rec_paper>
    <read_word total_score="4.2" accuracy_score="4" fluency_score="3.5"
      integrity_score="5" is_rejected="true" />
    </rec_paper></read_word></xml_result>"""
    result = parse_ise_result(xml)

    assert result.overall_score == 84.0
    assert result.accuracy_score == 80.0
    assert result.fluency_score == 70.0
    assert result.completeness_score == 100.0
    assert result.rejected is True


def test_percentage_request_context_preserves_genuinely_low_score() -> None:
    xml = """<xml_result><read_word total_score="4.2"
    accuracy_score="4" fluency_score="3.5" integrity_score="5" /></xml_result>"""

    result = parse_ise_result(xml, percentage_scores=True)

    assert result.overall_score == 4.2
    assert result.accuracy_score == 4.0
    assert result.fluency_score == 3.5
    assert result.completeness_score == 5.0


@pytest.mark.parametrize("payload", ["", "<broken>", "<xml_result />"])
def test_parser_maps_empty_malformed_or_unscored_result(payload: str) -> None:
    with pytest.raises(ISEParseError):
        parse_ise_result(payload)


@pytest.mark.asyncio
async def test_xunfei_gateway_consumes_final_base64_xml(tmp_path: Path) -> None:
    audio_path = tmp_path / "reading.mp3"
    audio_path.write_bytes(b"mock mp3")

    class Socket:
        def __init__(self) -> None:
            self.sent: list[dict] = []

        async def send(self, message: str) -> None:
            self.sent.append(json.loads(message))

        def __aiter__(self):
            async def messages():
                yield json.dumps(
                    {
                        "code": 0,
                        "sid": "sanitized-session",
                        "data": {
                            "status": 2,
                            "data": base64.b64encode(PERCENTAGE_XML.encode()).decode(),
                        },
                    }
                )

            return messages()

    socket = Socket()

    class Connection:
        async def __aenter__(self):
            return socket

        async def __aexit__(self, *_args):
            return False

    gateway = XunfeiISEPronunciationGateway(
        XunfeiISEConfig(app_id="app", api_key="key", api_secret="secret"),
        connector=lambda *_args, **_kwargs: Connection(),
    )
    result = await gateway.evaluate(
        reference_text="banana",
        audio_path=audio_path,
        category="read_word",
    )

    assert result.overall_score == 86.4
    assert socket.sent[0]["business"]["cmd"] == "ssb"
    assert socket.sent[1]["business"]["aus"] == 1


@pytest.mark.asyncio
async def test_fake_provider_is_offline(tmp_path: Path) -> None:
    gateway = create_pronunciation_gateway("fake")
    assert isinstance(gateway, FakePronunciationGateway)
    result = await gateway.evaluate(
        reference_text="banana",
        audio_path=tmp_path / "not-read.mp3",
        category="read_word",
    )
    assert result.overall_score == 88.0


def test_production_forbids_fake_pronunciation_provider(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(PronunciationConfigurationError, match="Fake providers"):
        create_pronunciation_gateway("fake")
