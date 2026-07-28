"""Workbook version-comparison orchestration."""

from __future__ import annotations

from pathlib import Path

from sheetpilot_beacon.adapters.xlsx import (
    WorkbookReadConfig,
    read_workbook,
    sha256_file,
)
from sheetpilot_beacon.domain.drift import compare_snapshots
from sheetpilot_beacon.domain.models import DriftReport
from sheetpilot_beacon.services.audit import SourceWorkbookChangedError


def compare_workbooks(
    before_path: str | Path,
    after_path: str | Path,
    *,
    reader_config: WorkbookReadConfig | None = None,
) -> DriftReport:
    """Compare two `.xlsx` files and verify both remain byte-identical."""

    before = Path(before_path)
    after = Path(after_path)
    before_hash = sha256_file(before)
    after_hash = sha256_file(after)
    before_snapshot = read_workbook(before, config=reader_config)
    after_snapshot = read_workbook(after, config=reader_config)
    if before_snapshot.sha256 != before_hash or after_snapshot.sha256 != after_hash:
        raise SourceWorkbookChangedError("a workbook changed while versions were parsed")
    report = compare_snapshots(before_snapshot, after_snapshot)
    if sha256_file(before) != before_hash or sha256_file(after) != after_hash:
        raise SourceWorkbookChangedError("a workbook changed during version comparison")
    return report
