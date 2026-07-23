"""Regenerate the repository's deterministic example workbooks."""

from __future__ import annotations

import argparse
from pathlib import Path

from sheetpilot_beacon.adapters.samples import generate_sample_workbooks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("examples"),
        help="directory that receives the three .xlsx files",
    )
    arguments = parser.parse_args()
    for name, path in generate_sample_workbooks(arguments.output_dir).items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
