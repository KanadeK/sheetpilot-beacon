from __future__ import annotations

from pathlib import Path

from scripts.secret_scan import scan


def test_secret_scan_detects_token_and_honors_explicit_synthetic_allowance(
    tmp_path: Path,
) -> None:
    exposed = tmp_path / "exposed.txt"
    exposed.write_text(
        "api_key=sk-ABCDEFGHIJKLMNOPQRSTUV\n",  # secret-scan: allow
        encoding="utf-8",
    )
    allowed = tmp_path / "allowed.txt"
    allowed.write_text(
        "api_key=sk-ABCDEFGHIJKLMNOPQRSTUV  # secret-scan: allow\n",
        encoding="utf-8",
    )

    findings = scan([exposed, allowed])

    assert [(finding.path, finding.line, finding.pattern) for finding in findings] == [
        (exposed, 1, "openai-token"),
        (exposed, 1, "assigned-secret"),
    ]


def test_secret_scan_skips_binary_payloads(tmp_path: Path) -> None:
    binary = tmp_path / "archive.bin"
    binary.write_bytes(b"\0sk-ABCDEFGHIJKLMNOPQRSTUV")

    assert scan([binary]) == []
