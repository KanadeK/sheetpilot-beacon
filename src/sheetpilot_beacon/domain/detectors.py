"""Evidence-backed static workbook risk detectors."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

import networkx as nx

from sheetpilot_beacon.domain.formulas import (
    canonical_formula,
    parse_formula_references,
)
from sheetpilot_beacon.domain.graph import build_dependency_graph
from sheetpilot_beacon.domain.models import (
    SEVERITY_RANK,
    AuditIssue,
    CellRecord,
    CellValueKind,
    IssueCode,
    Severity,
    SheetVisibility,
    WorkbookSnapshot,
)
from sheetpilot_beacon.domain.redaction import redact_sensitive_text

type IssueKey = tuple[IssueCode, str, str]


@dataclass(frozen=True, slots=True)
class DetectorConfig:
    """Thresholds that make detector behavior explicit and testable."""

    fanout_threshold: int = 8
    minimum_pattern_formulas: int = 3
    inconsistency_consensus: float = 0.75
    max_range_cells: int = 10_000

    def __post_init__(self) -> None:
        if self.fanout_threshold < 2:
            raise ValueError("fanout_threshold must be at least 2")
        if self.minimum_pattern_formulas < 3:
            raise ValueError("minimum_pattern_formulas must be at least 3")
        if not 0.5 < self.inconsistency_consensus <= 1:
            raise ValueError("inconsistency_consensus must be in (0.5, 1]")
        if self.max_range_cells < 1:
            raise ValueError("max_range_cells must be positive")


def _formula_excerpt(cell: CellRecord) -> str | None:
    if cell.formula is None:
        return None
    return redact_sensitive_text(cell.formula, limit=240)


def _add_issue(
    issues: dict[IssueKey, AuditIssue],
    issue: AuditIssue,
) -> None:
    issues.setdefault((issue.code, issue.sheet, issue.cell), issue)


def _group_cells(
    snapshot: WorkbookSnapshot,
    *,
    by_row: bool,
) -> dict[tuple[str, int], list[CellRecord]]:
    grouped: dict[tuple[str, int], list[CellRecord]] = defaultdict(list)
    for cell in snapshot.cells:
        axis = cell.row if by_row else cell.column
        grouped[(cell.sheet, axis)].append(cell)
    for cells in grouped.values():
        cells.sort(key=lambda cell: cell.column if by_row else cell.row)
    return grouped


def _position(cell: CellRecord, *, by_row: bool) -> int:
    return cell.column if by_row else cell.row


def _detect_hardcoded_intrusions(
    snapshot: WorkbookSnapshot,
    config: DetectorConfig,
    issues: dict[IssueKey, AuditIssue],
) -> None:
    constant_kinds = {
        CellValueKind.NUMBER,
        CellValueKind.DATE,
        CellValueKind.BOOLEAN,
    }
    for by_row in (True, False):
        for cells in _group_cells(snapshot, by_row=by_row).values():
            formulas = [cell for cell in cells if cell.formula is not None]
            if len(formulas) < config.minimum_pattern_formulas:
                continue
            positions = [_position(cell, by_row=by_row) for cell in formulas]
            low, high = min(positions), max(positions)
            if high - low + 1 > len(formulas) + 1:
                continue
            for cell in cells:
                position = _position(cell, by_row=by_row)
                if low < position < high and cell.value_kind in constant_kinds:
                    _add_issue(
                        issues,
                        AuditIssue(
                            code=IssueCode.HARDCODED_INTRUSION,
                            severity=Severity.HIGH,
                            sheet=cell.sheet,
                            cell=cell.coordinate,
                            title="Hardcoded value interrupts a formula pattern",
                            evidence=(
                                f"A constant sits between {len(formulas)} formulas "
                                f"along the same {'row' if by_row else 'column'}."
                            ),
                            recommendation=(
                                "Confirm whether the constant is intentional; restore a copied "
                                "formula or move the assumption to a labeled input cell."
                            ),
                            metadata={"pattern_formula_count": len(formulas)},
                        ),
                    )


def _detect_formula_inconsistencies(
    snapshot: WorkbookSnapshot,
    config: DetectorConfig,
    issues: dict[IssueKey, AuditIssue],
) -> None:
    for by_row in (True, False):
        for cells in _group_cells(snapshot, by_row=by_row).values():
            formulas = [cell for cell in cells if cell.formula is not None]
            if len(formulas) < config.minimum_pattern_formulas + 1:
                continue
            positions = [_position(cell, by_row=by_row) for cell in formulas]
            if max(positions) - min(positions) + 1 > len(formulas) + 1:
                continue
            patterns = {
                cell.node_id: canonical_formula(cell.formula or "", origin=cell.coordinate)
                for cell in formulas
            }
            counts = Counter(patterns.values())
            expected, expected_count = counts.most_common(1)[0]
            if expected_count / len(formulas) < config.inconsistency_consensus:
                continue
            for cell in formulas:
                if patterns[cell.node_id] == expected:
                    continue
                _add_issue(
                    issues,
                    AuditIssue(
                        code=IssueCode.FORMULA_INCONSISTENCY,
                        severity=Severity.HIGH,
                        sheet=cell.sheet,
                        cell=cell.coordinate,
                        title="Formula differs from the dominant copy pattern",
                        evidence=(
                            f"{expected_count} of {len(formulas)} neighboring formulas "
                            "share one relative-reference pattern."
                        ),
                        recommendation=(
                            "Compare the outlier with adjacent periods or rows and correct "
                            "the reference pattern if the deviation is not intentional."
                        ),
                        formula_excerpt=_formula_excerpt(cell),
                        metadata={
                            "matching_formulas": expected_count,
                            "pattern_formulas": len(formulas),
                        },
                    ),
                )


def _detect_broken_references(
    snapshot: WorkbookSnapshot,
    config: DetectorConfig,
    issues: dict[IssueKey, AuditIssue],
) -> None:
    for cell in snapshot.cells:
        if cell.formula is None:
            continue
        explicit_error = "#REF!" in cell.formula.upper()
        references = parse_formula_references(
            cell.formula,
            current_sheet=cell.sheet,
            named_ranges=snapshot.named_range_map,
            max_range_cells=config.max_range_cells,
        )
        missing_sheets = sorted(
            {
                reference.sheet
                for reference in references
                if reference.external_book is None and reference.sheet not in snapshot.sheet_names
            }
        )
        if not explicit_error and not missing_sheets:
            continue
        evidence = (
            "The formula contains an explicit #REF! token."
            if explicit_error
            else f"The formula targets missing sheet(s): {', '.join(missing_sheets)}."
        )
        _add_issue(
            issues,
            AuditIssue(
                code=IssueCode.BROKEN_REFERENCE,
                severity=Severity.CRITICAL,
                sheet=cell.sheet,
                cell=cell.coordinate,
                title="Formula contains an invalid reference",
                evidence=evidence,
                recommendation=(
                    "Restore the deleted range or update the formula to an existing, "
                    "verified source."
                ),
                formula_excerpt=_formula_excerpt(cell),
            ),
        )


def _detect_graph_risks(
    snapshot: WorkbookSnapshot,
    config: DetectorConfig,
    issues: dict[IssueKey, AuditIssue],
) -> None:
    graph = build_dependency_graph(
        snapshot,
        max_range_cells=config.max_range_cells,
    )
    cells = snapshot.cell_map
    for node_id, degree in graph.out_degree:
        if degree < config.fanout_threshold or node_id not in cells:
            continue
        cell = cells[node_id]
        _add_issue(
            issues,
            AuditIssue(
                code=IssueCode.HIGH_FANOUT,
                severity=Severity.MEDIUM,
                sheet=cell.sheet,
                cell=cell.coordinate,
                title="Cell has high downstream impact",
                evidence=f"The cell feeds {degree} formula cells.",
                recommendation=(
                    "Treat changes as high impact, document the assumption, and review "
                    "all downstream outputs before release."
                ),
                metadata={"dependent_count": degree},
            ),
        )

    sheet_map = snapshot.sheet_map
    hidden_sources: dict[str, set[str]] = defaultdict(set)
    external_sources: dict[str, set[str]] = defaultdict(set)
    for source, target, data in graph.edges(data=True):
        source_node = graph.nodes[source]
        target_cell = cells.get(target)
        if target_cell is None:
            continue
        source_sheet = str(source_node["sheet"])
        if (
            source_sheet in sheet_map
            and sheet_map[source_sheet].visibility is not SheetVisibility.VISIBLE
            and sheet_map[target_cell.sheet].visibility is SheetVisibility.VISIBLE
        ):
            hidden_sources[target].add(source_sheet)
        if bool(data.get("external")):
            external_sources[target].add(source_sheet)

    for target, source_sheets in hidden_sources.items():
        cell = cells[target]
        sources = ", ".join(sorted(source_sheets))
        _add_issue(
            issues,
            AuditIssue(
                code=IssueCode.HIDDEN_DEPENDENCY,
                severity=Severity.MEDIUM,
                sheet=cell.sheet,
                cell=cell.coordinate,
                title="Visible formula depends on a hidden sheet",
                evidence=f"Hidden source sheet(s): {sources}.",
                recommendation=(
                    "Document and review hidden inputs, or surface governed assumptions "
                    "on a visible sheet."
                ),
                formula_excerpt=_formula_excerpt(cell),
                metadata={"hidden_source_count": len(source_sheets)},
            ),
        )

    for target, source_sheets in external_sources.items():
        cell = cells[target]
        sources = ", ".join(
            redact_sensitive_text(source, limit=120) for source in sorted(source_sheets)
        )
        _add_issue(
            issues,
            AuditIssue(
                code=IssueCode.EXTERNAL_LINK,
                severity=Severity.HIGH,
                sheet=cell.sheet,
                cell=cell.coordinate,
                title="Formula depends on an external workbook",
                evidence=f"External source(s): {sources}.",
                recommendation=(
                    "Verify the linked workbook, owner, refresh process, and fallback "
                    "behavior before distributing the model."
                ),
                formula_excerpt=_formula_excerpt(cell),
                metadata={"external_source_count": len(source_sheets)},
            ),
        )

    for component in nx.strongly_connected_components(graph):
        cyclic = len(component) > 1 or any(graph.has_edge(node, node) for node in component)
        if not cyclic:
            continue
        internal_cells = sorted(node for node in component if node in cells)
        for node_id in internal_cells:
            cell = cells[node_id]
            _add_issue(
                issues,
                AuditIssue(
                    code=IssueCode.CIRCULAR_REFERENCE,
                    severity=Severity.CRITICAL,
                    sheet=cell.sheet,
                    cell=cell.coordinate,
                    title="Formula participates in a dependency cycle",
                    evidence=(
                        f"Cycle contains {len(internal_cells)} workbook cell(s): "
                        f"{', '.join(internal_cells[:6])}."
                    ),
                    recommendation=(
                        "Break the unintended cycle or document and independently verify "
                        "the required iterative calculation."
                    ),
                    formula_excerpt=_formula_excerpt(cell),
                    metadata={"cycle_cell_count": len(internal_cells)},
                ),
            )


def detect_issues(
    snapshot: WorkbookSnapshot,
    config: DetectorConfig | None = None,
) -> tuple[AuditIssue, ...]:
    """Run every detector and return stable, de-duplicated findings."""

    effective = config or DetectorConfig()
    issues: dict[IssueKey, AuditIssue] = {}
    _detect_hardcoded_intrusions(snapshot, effective, issues)
    _detect_formula_inconsistencies(snapshot, effective, issues)
    _detect_broken_references(snapshot, effective, issues)
    _detect_graph_risks(snapshot, effective, issues)
    return tuple(
        sorted(
            issues.values(),
            key=lambda issue: (
                SEVERITY_RANK[issue.severity],
                issue.sheet.casefold(),
                issue.cell,
                issue.code.value,
            ),
        )
    )
