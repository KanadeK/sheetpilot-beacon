"""Formula and workbook-structure drift comparison."""

from __future__ import annotations

from collections import Counter

from sheetpilot_beacon.domain.models import (
    CellRecord,
    CellValueKind,
    DriftChange,
    DriftKind,
    DriftReport,
    WorkbookSnapshot,
)
from sheetpilot_beacon.domain.redaction import redact_sensitive_text


def _formula(cell: CellRecord | None) -> str | None:
    if cell is None or cell.formula is None:
        return None
    return redact_sensitive_text(cell.formula, limit=300)


def _cell_change(
    before: CellRecord | None,
    after: CellRecord | None,
) -> DriftKind | None:
    before_formula = before is not None and before.formula is not None
    after_formula = after is not None and after.formula is not None
    if before_formula and after_formula:
        return (
            DriftKind.FORMULA_CHANGED
            if before is not None and after is not None and before.formula != after.formula
            else None
        )
    if before_formula:
        if after is not None and after.value_kind is not CellValueKind.BLANK:
            return DriftKind.FORMULA_REPLACED_BY_CONSTANT
        return DriftKind.FORMULA_REMOVED
    if after_formula:
        if before is not None and before.value_kind is not CellValueKind.BLANK:
            return DriftKind.CONSTANT_REPLACED_BY_FORMULA
        return DriftKind.FORMULA_ADDED
    if (
        before is not None
        and after is not None
        and before.value_fingerprint is not None
        and after.value_fingerprint is not None
        and before.value_fingerprint != after.value_fingerprint
    ):
        return DriftKind.CONSTANT_CHANGED
    return None


def compare_snapshots(
    before: WorkbookSnapshot,
    after: WorkbookSnapshot,
) -> DriftReport:
    """Compare cell semantics without exposing constant values."""

    changes: list[DriftChange] = []
    before_sheets = before.sheet_names
    after_sheets = after.sheet_names
    for sheet in sorted(after_sheets - before_sheets):
        changes.append(DriftChange(kind=DriftKind.SHEET_ADDED, sheet=sheet))
    for sheet in sorted(before_sheets - after_sheets):
        changes.append(DriftChange(kind=DriftKind.SHEET_REMOVED, sheet=sheet))

    before_cells = before.cell_map
    after_cells = after.cell_map
    for node_id in sorted(set(before_cells) | set(after_cells)):
        old = before_cells.get(node_id)
        new = after_cells.get(node_id)
        kind = _cell_change(old, new)
        if kind is None:
            continue
        source = old or new
        if source is None:  # pragma: no cover - union guarantees one side
            continue
        changes.append(
            DriftChange(
                kind=kind,
                sheet=source.sheet,
                cell=source.coordinate,
                before_formula=_formula(old),
                after_formula=_formula(new),
                before_value_kind=old.value_kind if old else None,
                after_value_kind=new.value_kind if new else None,
            )
        )

    counts = Counter(change.kind for change in changes)
    summary = {kind: counts[kind] for kind in DriftKind if counts[kind]}
    return DriftReport(
        before_filename=before.filename,
        after_filename=after.filename,
        before_sha256=before.sha256,
        after_sha256=after.sha256,
        changes=tuple(changes),
        summary=summary,
    )
