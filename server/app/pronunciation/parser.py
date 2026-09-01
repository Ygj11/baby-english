"""Parse provider XML into provider-neutral pronunciation scores."""

import xml.etree.ElementTree as ET

from server.app.pronunciation.domain import (
    PronunciationIssue,
    PronunciationResult,
    WordPronunciationScore,
)


_FILLERS = {"sil", "silv", "fil"}
_DP_ISSUES = {
    "16": "omitted",
    "32": "inserted",
    "64": "repeated",
    "128": "substituted",
}


class ISEParseError(ValueError):
    """Raised when an ISE payload has no usable scored result."""


def parse_ise_result(
    xml_payload: str,
    *,
    percentage_scores: bool | None = None,
) -> PronunciationResult:
    if not xml_payload.strip():
        raise ISEParseError("ISE returned an empty result.")
    try:
        root = ET.fromstring(xml_payload)
    except ET.ParseError as error:
        raise ISEParseError("ISE returned malformed result XML.") from error

    scored = _find_scored_node(root)
    if scored is None:
        raise ISEParseError("ISE returned no scored result.")

    scale = 1.0 if percentage_scores is True else _score_scale(scored)
    attributes = scored.attrib
    overall = _required_score(attributes.get("total_score"), scale)
    accuracy = _optional_score(
        attributes.get("accuracy_score") or attributes.get("accuracy_socre"), scale
    )
    fluency = _optional_score(attributes.get("fluency_score"), scale)
    completeness = _optional_score(attributes.get("integrity_score"), scale)
    standard = _optional_score(attributes.get("standard_score"), scale)

    return PronunciationResult(
        overall_score=overall,
        accuracy_score=accuracy if accuracy is not None else overall,
        fluency_score=fluency if fluency is not None else overall,
        completeness_score=completeness,
        standard_score=standard,
        rejected=_as_bool(attributes.get("is_rejected")),
        words=tuple(_parse_words(scored, scale)),
    )


def _find_scored_node(root: ET.Element) -> ET.Element | None:
    preferred = {"read_word", "read_sentence"}
    for element in root.iter():
        if _local_name(element.tag) in preferred and "total_score" in element.attrib:
            return element
    for element in root.iter():
        if "total_score" in element.attrib:
            return element
    return None


def _score_scale(element: ET.Element) -> float:
    values: list[float] = []
    for name in (
        "total_score",
        "accuracy_score",
        "accuracy_socre",
        "fluency_score",
        "integrity_score",
        "standard_score",
    ):
        try:
            values.append(float(element.attrib[name]))
        except (KeyError, TypeError, ValueError):
            pass
    return 20.0 if values and max(values) <= 5.0 else 1.0


def _required_score(value: str | None, scale: float) -> float:
    score = _optional_score(value, scale)
    if score is None:
        raise ISEParseError("ISE result has no total score.")
    return score


def _optional_score(value: str | None, scale: float) -> float | None:
    if value is None:
        return None
    try:
        return round(max(0.0, min(100.0, float(value) * scale)), 1)
    except (TypeError, ValueError):
        return None


def _parse_words(scored: ET.Element, scale: float) -> list[WordPronunciationScore]:
    words: list[WordPronunciationScore] = []
    for element in scored.iter():
        if _local_name(element.tag) != "word":
            continue
        content = (element.attrib.get("content") or "").strip()
        if not content or content.lower() in _FILLERS:
            continue
        issues = _word_issues(element)
        words.append(
            WordPronunciationScore(
                word=content,
                score=_optional_score(element.attrib.get("total_score"), scale),
                issues=tuple(issues),
            )
        )
    return words


def _word_issues(word: ET.Element) -> list[PronunciationIssue]:
    issues: list[PronunciationIssue] = []
    _append_dp_issue(issues, word.attrib.get("dp_message"))
    if word.attrib.get("werr_msg") not in {None, "", "0"}:
        issues.append(PronunciationIssue(kind="pronunciation_variance"))

    for element in word.iter():
        name = _local_name(element.tag)
        if name not in {"syll", "phone"}:
            continue
        unit = (element.attrib.get("content") or "").strip()
        if not unit or unit.lower() in _FILLERS:
            continue
        code = element.attrib.get("dp_message")
        if code in _DP_ISSUES:
            issues.append(PronunciationIssue(kind=_DP_ISSUES[code], unit=unit))
        elif element.attrib.get("serr_msg") not in {None, "", "0"}:
            issues.append(PronunciationIssue(kind="pronunciation_variance", unit=unit))
    return issues


def _append_dp_issue(issues: list[PronunciationIssue], code: str | None) -> None:
    if code in _DP_ISSUES:
        issues.append(PronunciationIssue(kind=_DP_ISSUES[code]))


def _as_bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes"}


def _local_name(tag: str) -> str:
    return tag.rsplit("}", maxsplit=1)[-1]
