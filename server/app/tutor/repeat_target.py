"""Extract an explicit, stable pronunciation target from a Tutor reply."""

from server.app.pronunciation.reference import (
    InvalidReferenceTextError,
    normalize_reference_text,
)


REPEAT_MARKER = "Repeat after me:"


def extract_repeat_target(reply: str) -> str | None:
    if reply.count(REPEAT_MARKER) != 1:
        return None
    _prefix, target = reply.rsplit(REPEAT_MARKER, maxsplit=1)
    try:
        return normalize_reference_text(target)
    except InvalidReferenceTextError:
        return None
