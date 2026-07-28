"""Cross-platform quality-gate entry point."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path


def _commands(basetemp: Path) -> tuple[Sequence[str], ...]:
    return (
        (sys.executable, "-m", "ruff", "check", "."),
        (sys.executable, "-m", "ruff", "format", "--check", "."),
        (sys.executable, "-m", "mypy", "src"),
        (
            sys.executable,
            "-m",
            "pytest",
            "-q",
            f"--basetemp={basetemp}",
            "--cov=src",
            "--cov-report=term-missing",
            "--cov-fail-under=80",
        ),
        (sys.executable, "-m", "build"),
    )


def main() -> int:
    """Run every local quality gate and stop on the first failure."""
    with tempfile.TemporaryDirectory(dir=Path.cwd(), prefix=".pytest-tmp-verify-") as temp_dir:
        for command in _commands(Path(temp_dir)):
            subprocess.run(command, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
