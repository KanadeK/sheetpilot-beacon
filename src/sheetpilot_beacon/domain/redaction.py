"""Redaction helpers for formula and external-link evidence."""

from __future__ import annotations

import re

ASSIGNMENT_SECRET = re.compile(
    r"(?i)\b("
    r"api[_-]?key|access[_-]?token|auth[_-]?token|token|password|passwd|secret|"
    r"signature|sig"
    r")(\s*[:=]\s*)([^&\s\"')]+)"
)
TOKEN_SECRET = re.compile(
    r"(?i)\b(?:"
    r"gh[pousr]_[A-Za-z0-9]{20,}|"
    r"sk-[A-Za-z0-9_-]{16,}|"
    r"xox[baprs]-[A-Za-z0-9-]{16,}"
    r")"
)


def redact_sensitive_text(text: str, *, limit: int | None = None) -> str:
    """Mask credential-shaped evidence while retaining structural context."""

    redacted = ASSIGNMENT_SECRET.sub(
        lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]",
        text,
    )
    redacted = TOKEN_SECRET.sub("[REDACTED]", redacted)
    if limit is not None and len(redacted) > limit:
        return f"{redacted[: max(0, limit - 1)]}…"
    return redacted
