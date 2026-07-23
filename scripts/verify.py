"""Cross-platform quality-gate entry point."""

from __future__ import annotations

import subprocess
import sys

COMMANDS = (
    (sys.executable, "-m", "ruff", "check", "."),
    (sys.executable, "-m", "ruff", "format", "--check", "."),
    (sys.executable, "-m", "mypy", "src"),
    (
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "--cov=src",
        "--cov-report=term-missing",
        "--cov-fail-under=80",
    ),
    (sys.executable, "-m", "build"),
)


def main() -> int:
    """Run every local quality gate and stop on the first failure."""
    for command in COMMANDS:
        subprocess.run(command, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
