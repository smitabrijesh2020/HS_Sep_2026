"""Shared error-message redaction, generalized from the pattern originally
written as `services.communication_service._sanitize_error`.

Any exception text that might reach an audit log, an on-screen error, or a
report needs to pass through here first - real workbook paths/contents can
end up embedded in exception messages (e.g. a file-not-found error includes
the full path), and lower layers occasionally leak token/secret-looking
strings.
"""
from __future__ import annotations

from collections.abc import Sequence

_DEFAULT_MARKERS: tuple[str, ...] = ("token", "secret", "password", "authorization")


def sanitize_error(
    error: str | None,
    extra_markers: Sequence[str] = (),
    max_len: int = 500,
) -> str | None:
    """Redact if the lowered text contains a sensitive marker, else truncate.

    `extra_markers` lets a caller flag additional sensitive substrings for
    this call site (e.g. a real local folder path fragment) without widening
    the default marker list for everyone.
    """
    if not error:
        return error
    lowered = error.lower()
    for marker in (*_DEFAULT_MARKERS, *extra_markers):
        if marker and marker.lower() in lowered:
            return "Sanitized error (sensitive content redacted)."
    return error[:max_len]
