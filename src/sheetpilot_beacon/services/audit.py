"""Workbook audit orchestration and source-integrity checks."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from sheetpilot_beacon import __version__
from sheetpilot_beacon.adapters.xlsx import (
    WorkbookReadConfig,
    read_workbook,
    sha256_file,
)
from sheetpilot_beacon.domain.detectors import DetectorConfig, detect_issues
from sheetpilot_beacon.domain.graph import build_dependency_graph
from sheetpilot_beacon.domain.models import (
    AuditMetrics,
    AuditReport,
    IssueCode,
    Severity,
    SheetVisibility,
)
from sheetpilot_beacon.domain.redaction import redact_sensitive_text


class SourceWorkbookChangedError(RuntimeError):
    """Raised if the input bytes change during a supposedly read-only audit."""


class Clock(Protocol):
    def now(self) -> datetime:
        """Return an aware timestamp."""


@dataclass(frozen=True, slots=True)
class FixedClock:
    """Deterministic clock used by tests and reproducible demos."""

    value: datetime

    def __post_init__(self) -> None:
        if self.value.tzinfo is None:
            raise ValueError("FixedClock requires an aware datetime")

    def now(self) -> datetime:
        return self.value


@dataclass(frozen=True, slots=True)
class SystemClock:
    """UTC wall clock used by interactive runs."""

    def now(self) -> datetime:
        return datetime.now(UTC)


def audit_workbook(
    workbook_path: str | Path,
    *,
    detector_config: DetectorConfig | None = None,
    reader_config: WorkbookReadConfig | None = None,
    clock: Clock | None = None,
) -> AuditReport:
    """Audit one workbook and prove its bytes were not changed."""

    path = Path(workbook_path)
    before_hash = sha256_file(path)
    snapshot = read_workbook(path, config=reader_config)
    if snapshot.sha256 != before_hash:
        raise SourceWorkbookChangedError("source changed while it was being parsed")

    config = detector_config or DetectorConfig()
    issues = detect_issues(snapshot, config)
    graph = build_dependency_graph(snapshot, max_range_cells=config.max_range_cells)
    after_hash = sha256_file(path)
    if after_hash != before_hash:
        raise SourceWorkbookChangedError("source changed during audit")

    issue_counts = Counter(issue.code for issue in issues)
    severity_counts = Counter(issue.severity for issue in issues)
    formula_count = sum(cell.formula is not None for cell in snapshot.cells)
    metrics = AuditMetrics(
        sheet_count=len(snapshot.sheets),
        hidden_sheet_count=sum(
            sheet.visibility is not SheetVisibility.VISIBLE for sheet in snapshot.sheets
        ),
        populated_cell_count=len(snapshot.cells),
        formula_cell_count=formula_count,
        named_range_count=len(snapshot.named_ranges),
        merged_range_count=sum(len(sheet.merged_ranges) for sheet in snapshot.sheets),
        external_link_count=len(snapshot.external_links),
        dependency_node_count=graph.number_of_nodes(),
        dependency_edge_count=graph.number_of_edges(),
    )
    return AuditReport(
        tool_version=__version__,
        generated_at=(clock or SystemClock()).now(),
        source_filename=snapshot.filename,
        source_sha256=snapshot.sha256,
        source_unchanged=True,
        metrics=metrics,
        sheets=snapshot.sheets,
        named_ranges=snapshot.named_ranges,
        external_links=tuple(
            redact_sensitive_text(link, limit=300) for link in snapshot.external_links
        ),
        issues=issues,
        issue_summary={code: issue_counts[code] for code in IssueCode if issue_counts[code]},
        severity_summary={
            severity: severity_counts[severity]
            for severity in Severity
            if severity_counts[severity]
        },
    )
