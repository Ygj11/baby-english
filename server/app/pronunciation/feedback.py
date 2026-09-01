"""Short deterministic child-facing pronunciation feedback."""

from server.app.pronunciation.domain import PronunciationResult


def child_feedback(result: PronunciationResult) -> str:
    if result.rejected:
        return "这次好像没有读到目标词或句子，我们重新读一次吧。"
    if result.overall_score >= 85:
        return "很棒！读得很清楚，再读一次巩固一下。"
    if result.overall_score >= 65:
        return "不错！慢一点，再试一次会更清楚。"
    return "我们再来一次，先慢慢读，不着急。"
