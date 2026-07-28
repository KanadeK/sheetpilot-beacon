"""Command-line interface for offline workbook audits and formula drift."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

from sheetpilot_beacon import __version__
from sheetpilot_beacon.adapters.exporters import (
    export_annotated_workbook,
    export_drift_html,
    export_drift_json,
    export_html_report,
    export_json_report,
)
from sheetpilot_beacon.adapters.xlsx import WorkbookInputError
from sheetpilot_beacon.domain.detectors import DetectorConfig
from sheetpilot_beacon.domain.models import SEVERITY_RANK, Severity
from sheetpilot_beacon.services.audit import SourceWorkbookChangedError, audit_workbook
from sheetpilot_beacon.services.demo import run_demo
from sheetpilot_beacon.services.diff import compare_workbooks


def severity_exit_code(
    severities: Iterable[Severity],
    *,
    fail_on: Severity | None,
) -> int:
    """Return 3 when any finding meets the requested failure threshold."""

    if fail_on is None:
        return 0
    threshold = SEVERITY_RANK[fail_on]
    return 3 if any(SEVERITY_RANK[severity] <= threshold for severity in severities) else 0


def _scan(arguments: argparse.Namespace) -> int:
    source = Path(arguments.workbook)
    report = audit_workbook(
        source,
        detector_config=DetectorConfig(fanout_threshold=arguments.fanout_threshold),
    )
    output = Path(arguments.output_dir)
    stem = source.stem
    html_path = export_html_report(report, output / f"{stem}.audit.html")
    json_path = export_json_report(report, output / f"{stem}.audit.json")
    xlsx_path = export_annotated_workbook(
        source,
        report,
        output / f"{stem}.annotated.xlsx",
    )
    print(
        f"{source.name}: {len(report.issues)} findings, "
        f"{report.metrics.formula_cell_count} formulas, "
        f"{report.metrics.dependency_edge_count} dependency edges"
    )
    print(f"HTML: {html_path}")
    print(f"JSON: {json_path}")
    print(f"Annotated workbook: {xlsx_path}")
    fail_on = Severity(arguments.fail_on) if arguments.fail_on != "none" else None
    return severity_exit_code(
        (issue.severity for issue in report.issues),
        fail_on=fail_on,
    )


def _diff(arguments: argparse.Namespace) -> int:
    before = Path(arguments.before)
    after = Path(arguments.after)
    report = compare_workbooks(before, after)
    output = Path(arguments.output_dir)
    stem = f"{before.stem}-to-{after.stem}"
    html_path = export_drift_html(report, output / f"{stem}.drift.html")
    json_path = export_drift_json(report, output / f"{stem}.drift.json")
    print(f"{before.name} -> {after.name}: {len(report.changes)} changes")
    print(f"HTML: {html_path}")
    print(f"JSON: {json_path}")
    return 0


def _demo(arguments: argparse.Namespace) -> int:
    result = run_demo(arguments.samples_dir, arguments.output_dir)
    print(
        f"Demo audited {result.workbook_count} workbooks and found "
        f"{result.finding_count} seeded issues."
    )
    print(f"Index: {result.index_path}")
    return 0


def _web(arguments: argparse.Namespace) -> int:
    app_path = Path(__file__).with_name("app.py")
    command = (
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        str(arguments.port),
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    )
    return subprocess.run(command, check=False).returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sheetpilot",
        description="Offline Excel formula-risk, dependency, and drift auditing.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    scan = commands.add_parser("scan", help="audit one .xlsx workbook")
    scan.add_argument("workbook", type=Path)
    scan.add_argument("--output-dir", type=Path, default=Path("audit-output"))
    scan.add_argument("--fanout-threshold", type=int, default=8)
    scan.add_argument(
        "--fail-on",
        choices=("none", *(severity.value for severity in Severity)),
        default="none",
        help="return exit code 3 when this severity or higher is present",
    )
    scan.set_defaults(handler=_scan)

    diff = commands.add_parser("diff", help="compare formulas in two workbooks")
    diff.add_argument("before", type=Path)
    diff.add_argument("after", type=Path)
    diff.add_argument("--output-dir", type=Path, default=Path("drift-output"))
    diff.set_defaults(handler=_diff)

    demo = commands.add_parser("demo", help="audit all deterministic samples")
    demo.add_argument("--samples-dir", type=Path, default=Path("examples"))
    demo.add_argument("--output-dir", type=Path, default=Path("demo-output"))
    demo.set_defaults(handler=_demo)

    web = commands.add_parser("web", help="start the local Streamlit interface")
    web.add_argument("--port", type=int, default=8501)
    web.set_defaults(handler=_web)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse CLI arguments and convert expected user errors to exit code 1."""

    parser = build_parser()
    arguments = parser.parse_args(argv)
    try:
        return int(arguments.handler(arguments))
    except (
        FileNotFoundError,
        OSError,
        SourceWorkbookChangedError,
        ValueError,
        WorkbookInputError,
    ) as error:
        print(f"sheetpilot: error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
