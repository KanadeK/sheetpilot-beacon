"""Generate a complete offline demo from the committed sample workbooks."""

from __future__ import annotations

import argparse
from pathlib import Path

from sheetpilot_beacon.services.demo import run_demo


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples-dir", type=Path, default=Path("examples"))
    parser.add_argument("--output-dir", type=Path, default=Path("demo-output"))
    arguments = parser.parse_args()
    result = run_demo(arguments.samples_dir, arguments.output_dir)
    print(
        f"Audited {result.workbook_count} workbooks; "
        f"detected {result.finding_count} seeded findings."
    )
    print(f"Open {result.index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
