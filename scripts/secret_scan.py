"""Fail when tracked or untracked project files contain credential-shaped text."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

ALLOW_MARKER = "secret-scan: allow"
MAX_TEXT_BYTES = 5 * 1024 * 1024
BINARY_SUFFIXES = {
    ".gif",
    ".ico",
    ".jpg",
    ".jpeg",
    ".pdf",
    ".png",
    ".pyc",
    ".webp",
    ".whl",
    ".xlsx",
    ".zip",
}
PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:DSA |EC |OPENSSH |PGP |RSA )?PRIVATE KEY-----"),
    "github-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "openai-token": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "slack-token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{16,}\b"),
    "aws-access-key": re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    "assigned-secret": re.compile(
        r"""(?ix)
        \b(?:api[_-]?key|access[_-]?token|auth[_-]?token|password|passwd|secret)
        \s*[:=]\s*["']?
        (?!\[REDACTED\])([A-Za-z0-9_./+=-]{20,})
        """
    ),
}


@dataclass(frozen=True, slots=True)
class Finding:
    path: Path
    line: int
    pattern: str


def _project_files() -> list[Path]:
    result = subprocess.run(
        (
            "git",
            "-c",
            "safe.directory=*",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
        ),
        check=True,
        capture_output=True,
    )
    return [Path(raw.decode("utf-8")) for raw in result.stdout.split(b"\0") if raw]


def scan(paths: list[Path]) -> list[Finding]:
    """Return credential-shaped findings from bounded text files."""

    findings: list[Finding] = []
    for path in paths:
        if (
            not path.is_file()
            or path.suffix.casefold() in BINARY_SUFFIXES
            or path.stat().st_size > MAX_TEXT_BYTES
        ):
            continue
        payload = path.read_bytes()
        if b"\0" in payload[:4096]:
            continue
        for line_number, line in enumerate(
            payload.decode("utf-8", errors="replace").splitlines(),
            start=1,
        ):
            if ALLOW_MARKER in line:
                continue
            for name, pattern in PATTERNS.items():
                if pattern.search(line):
                    findings.append(Finding(path=path, line=line_number, pattern=name))
    return findings


def main() -> int:
    findings = scan(_project_files())
    if findings:
        for finding in findings:
            print(f"{finding.path}:{finding.line}: credential pattern {finding.pattern}")
        return 1
    print("Secret scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
