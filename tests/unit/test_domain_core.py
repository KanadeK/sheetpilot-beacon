from __future__ import annotations

from collections.abc import Iterable

import pytest

from sheetpilot_beacon.domain.detectors import DetectorConfig, detect_issues
from sheetpilot_beacon.domain.drift import compare_snapshots
from sheetpilot_beacon.domain.formulas import (
    canonical_formula,
    parse_formula_references,
)
from sheetpilot_beacon.domain.graph import build_dependency_graph, build_sheet_graph
from sheetpilot_beacon.domain.models import (
    CellRecord,
    CellValueKind,
    DriftKind,
    IssueCode,
    NamedRangeRecord,
    SheetRecord,
    SheetVisibility,
    WorkbookSnapshot,
)
from sheetpilot_beacon.domain.redaction import redact_sensitive_text


def make_cell(
    sheet: str,
    coordinate: str,
    *,
    formula: str | None = None,
    value_kind: CellValueKind = CellValueKind.NUMBER,
    value_fingerprint: str | None = None,
) -> CellRecord:
    if formula is not None:
        value_kind = CellValueKind.FORMULA
    return CellRecord(
        sheet=sheet,
        coordinate=coordinate,
        value_kind=value_kind,
        formula=formula,
        value_fingerprint=value_fingerprint,
    )


def make_snapshot(
    cells: Iterable[CellRecord],
    *,
    sheet_states: dict[str, SheetVisibility] | None = None,
    named_ranges: tuple[NamedRangeRecord, ...] = (),
    sha256: str = "a" * 64,
) -> WorkbookSnapshot:
    cell_tuple = tuple(cells)
    states = sheet_states or {}
    sheet_names = sorted({cell.sheet for cell in cell_tuple} | set(states))
    sheets = tuple(
        SheetRecord(
            name=name,
            visibility=states.get(name, SheetVisibility.VISIBLE),
            max_row=max(
                (cell.row for cell in cell_tuple if cell.sheet == name),
                default=1,
            ),
            max_column=max(
                (cell.column for cell in cell_tuple if cell.sheet == name),
                default=1,
            ),
        )
        for name in sheet_names
    )
    return WorkbookSnapshot(
        filename="synthetic.xlsx",
        sha256=sha256,
        sheets=sheets,
        cells=cell_tuple,
        named_ranges=named_ranges,
    )


def test_formula_parser_resolves_local_qualified_named_and_external_references() -> None:
    named = {"TaxRate": ("Assumptions!$B$2",)}
    formula = "=SUM(A1:B1)+'Hidden Data'!$C$2+TaxRate+'[legacy.xlsx]Rates'!D4+IF(E1=\"F2\",1,0)"

    references = parse_formula_references(
        formula,
        current_sheet="Model",
        named_ranges=named,
    )
    node_ids = {reference.node_id for reference in references}

    assert node_ids == {
        "Model!A1",
        "Model!B1",
        "Hidden Data!C2",
        "Assumptions!B2",
        "external:[legacy.xlsx]Rates!D4",
        "Model!E1",
    }
    external = next(reference for reference in references if reference.external_book)
    assert external.external_book == "legacy.xlsx"
    assert external.sheet == "Rates"


def test_large_ranges_are_symbolic_instead_of_expanded_without_bound() -> None:
    references = parse_formula_references(
        "=SUM(A1:A1000)",
        current_sheet="Model",
        max_range_cells=20,
    )

    assert len(references) == 1
    assert references[0].is_symbolic_range is True
    assert references[0].node_id == "Model!A1:A1000"


def test_canonical_formula_matches_copy_equivalent_patterns() -> None:
    first = canonical_formula("=B2*$A$1", origin="C2")
    second = canonical_formula("=C2*$A$1", origin="D2")

    assert first == second
    assert canonical_formula("=C2*$A$2", origin="D2") != first


def test_dependency_graph_tracks_cell_and_sheet_edges() -> None:
    snapshot = make_snapshot(
        (
            make_cell("Inputs", "A1"),
            make_cell("Model", "B2", formula="=Inputs!A1*2"),
            make_cell("Model", "C2", formula="=B2+1"),
        )
    )

    cell_graph = build_dependency_graph(snapshot)
    sheet_graph = build_sheet_graph(cell_graph)

    assert cell_graph.has_edge("Inputs!A1", "Model!B2")
    assert cell_graph.has_edge("Model!B2", "Model!C2")
    assert sheet_graph["Inputs"]["Model"]["reference_count"] == 1
    assert sheet_graph["Model"]["Model"]["reference_count"] == 1


def test_detector_suite_finds_real_structural_risks() -> None:
    cells = [
        make_cell("Inputs", "B2"),
        make_cell("Rates", "A1"),
        make_cell("Model", "B1"),
        make_cell("Model", "C1"),
        make_cell("Model", "D1"),
        make_cell("Model", "E1"),
        make_cell("Model", "F1"),
        make_cell("Model", "B2", formula="=Inputs!$B$2*B1"),
        make_cell("Model", "C2", formula="=Inputs!$B$2*C1"),
        make_cell("Model", "D2", formula="=Inputs!$B$2*D1"),
        make_cell("Model", "E2"),
        make_cell("Model", "F2", formula="=Inputs!$B$2*F1"),
        make_cell("Model", "B4", formula="=#REF!+1"),
        make_cell("Model", "B5"),
        make_cell("Model", "C5"),
        make_cell("Model", "D5"),
        make_cell("Model", "E5"),
        make_cell("Model", "B6", formula="=B5*2"),
        make_cell("Model", "C6", formula="=C5*2"),
        make_cell("Model", "D6", formula="=D5*3"),
        make_cell("Model", "E6", formula="=E5*2"),
        make_cell("Model", "B8", formula="=Rates!A1*2"),
        make_cell("Model", "B9", formula="='[legacy.xlsx]Rates'!A1*2"),
        make_cell("Model", "B10", formula="=C10"),
        make_cell("Model", "C10", formula="=B10"),
    ]
    snapshot = make_snapshot(
        cells,
        sheet_states={"Rates": SheetVisibility.HIDDEN},
    )

    issues = detect_issues(
        snapshot,
        DetectorConfig(
            fanout_threshold=4,
            minimum_pattern_formulas=3,
            inconsistency_consensus=0.75,
        ),
    )
    by_key = {(issue.code, issue.sheet, issue.cell) for issue in issues}

    assert (IssueCode.HARDCODED_INTRUSION, "Model", "E2") in by_key
    assert (IssueCode.BROKEN_REFERENCE, "Model", "B4") in by_key
    assert (IssueCode.FORMULA_INCONSISTENCY, "Model", "D6") in by_key
    assert (IssueCode.HIGH_FANOUT, "Inputs", "B2") in by_key
    assert (IssueCode.HIDDEN_DEPENDENCY, "Model", "B8") in by_key
    assert (IssueCode.EXTERNAL_LINK, "Model", "B9") in by_key
    assert (IssueCode.CIRCULAR_REFERENCE, "Model", "B10") in by_key
    assert (IssueCode.CIRCULAR_REFERENCE, "Model", "C10") in by_key


def test_broken_reference_includes_missing_sheet_target() -> None:
    snapshot = make_snapshot((make_cell("Model", "A1", formula="='Deleted Sheet'!B2+1"),))

    issues = detect_issues(snapshot)

    assert [(issue.code, issue.sheet, issue.cell) for issue in issues] == [
        (IssueCode.BROKEN_REFERENCE, "Model", "A1")
    ]


def test_drift_finds_formula_to_constant_and_changed_formula() -> None:
    before = make_snapshot(
        (
            make_cell("Model", "C3", formula="=A1+B1"),
            make_cell("Model", "D3", formula="=A2+B2"),
        ),
        sha256="b" * 64,
    )
    after = make_snapshot(
        (
            make_cell(
                "Model",
                "C3",
                value_fingerprint="constant-hash",
            ),
            make_cell("Model", "D3", formula="=A2-B2"),
        ),
        sha256="c" * 64,
    )

    report = compare_snapshots(before, after)
    changes = {(change.kind, change.sheet, change.cell) for change in report.changes}

    assert (DriftKind.FORMULA_REPLACED_BY_CONSTANT, "Model", "C3") in changes
    assert (DriftKind.FORMULA_CHANGED, "Model", "D3") in changes
    assert report.summary[DriftKind.FORMULA_REPLACED_BY_CONSTANT] == 1


@pytest.mark.parametrize(
    ("text", "forbidden"),
    [
        ("https://example.test/?api_key=super-secret-value", "super-secret-value"),
        ('="token=abc123456789"', "abc123456789"),
        ('=WEBSERVICE("https://x.test/?password=hunter2")', "hunter2"),
        ('=CONCAT("ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456")', "ghp_ABC"),  # secret-scan: allow
    ],
)
def test_sensitive_formula_evidence_is_redacted(text: str, forbidden: str) -> None:
    redacted = redact_sensitive_text(text)

    assert forbidden not in redacted
    assert "[REDACTED]" in redacted
