"""Typed domain records shared by every adapter and interface."""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

CELL_COORDINATE = re.compile(r"^(?P<column>[A-Z]{1,3})(?P<row>[1-9][0-9]*)$")


class SheetVisibility(StrEnum):
    """Open XML worksheet visibility states."""

    VISIBLE = "visible"
    HIDDEN = "hidden"
    VERY_HIDDEN = "veryHidden"


class CellValueKind(StrEnum):
    """Value classes retained without exposing raw workbook values."""

    BLANK = "blank"
    FORMULA = "formula"
    NUMBER = "number"
    TEXT = "text"
    BOOLEAN = "boolean"
    DATE = "date"
    ERROR = "error"


class Severity(StrEnum):
    """Stable issue priorities used by CLI, HTML, Excel, and Streamlit."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


SEVERITY_RANK: dict[Severity, int] = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
    Severity.INFO: 4,
}


class IssueCode(StrEnum):
    """Machine-readable detector identifiers."""

    HARDCODED_INTRUSION = "hardcoded_intrusion"
    BROKEN_REFERENCE = "broken_reference"
    FORMULA_INCONSISTENCY = "formula_inconsistency"
    HIGH_FANOUT = "high_fanout"
    HIDDEN_DEPENDENCY = "hidden_dependency"
    EXTERNAL_LINK = "external_link"
    CIRCULAR_REFERENCE = "circular_reference"


class DriftKind(StrEnum):
    """Workbook changes relevant to formula governance."""

    FORMULA_ADDED = "formula_added"
    FORMULA_REMOVED = "formula_removed"
    FORMULA_CHANGED = "formula_changed"
    FORMULA_REPLACED_BY_CONSTANT = "formula_replaced_by_constant"
    CONSTANT_REPLACED_BY_FORMULA = "constant_replaced_by_formula"
    CONSTANT_CHANGED = "constant_changed"
    SHEET_ADDED = "sheet_added"
    SHEET_REMOVED = "sheet_removed"


class DomainModel(BaseModel):
    """Strict immutable base for deterministic value objects."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class CellRecord(DomainModel):
    """A non-empty cell represented without its raw constant value."""

    sheet: str = Field(min_length=1)
    coordinate: str
    value_kind: CellValueKind
    formula: str | None = None
    value_fingerprint: str | None = None

    @model_validator(mode="after")
    def validate_cell(self) -> Self:
        coordinate = self.coordinate.replace("$", "").upper()
        if not CELL_COORDINATE.fullmatch(coordinate):
            raise ValueError(f"invalid A1 coordinate: {self.coordinate}")
        object.__setattr__(self, "coordinate", coordinate)
        if self.value_kind is CellValueKind.FORMULA:
            if self.formula is None or not self.formula.startswith("="):
                raise ValueError("formula cells require a formula beginning with '='")
        elif self.formula is not None:
            raise ValueError("non-formula cells cannot carry formula text")
        return self

    @property
    def row(self) -> int:
        """One-based row number."""
        match = CELL_COORDINATE.fullmatch(self.coordinate)
        if match is None:  # pragma: no cover - protected by validation
            raise ValueError(self.coordinate)
        return int(match.group("row"))

    @property
    def column(self) -> int:
        """One-based column number."""
        match = CELL_COORDINATE.fullmatch(self.coordinate)
        if match is None:  # pragma: no cover - protected by validation
            raise ValueError(self.coordinate)
        total = 0
        for character in match.group("column"):
            total = total * 26 + ord(character) - ord("A") + 1
        return total

    @property
    def node_id(self) -> str:
        """Stable dependency-graph identifier."""
        return f"{self.sheet}!{self.coordinate}"


class SheetRecord(DomainModel):
    """Worksheet structural metadata."""

    name: str = Field(min_length=1)
    visibility: SheetVisibility = SheetVisibility.VISIBLE
    max_row: int = Field(ge=1)
    max_column: int = Field(ge=1)
    merged_ranges: tuple[str, ...] = ()


class NamedRangeRecord(DomainModel):
    """Workbook defined name and its static destinations."""

    name: str = Field(min_length=1)
    destinations: tuple[str, ...]
    hidden: bool = False
    local_sheet: str | None = None


class WorkbookSnapshot(DomainModel):
    """Privacy-minimized, deterministic representation of one workbook."""

    filename: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    sheets: tuple[SheetRecord, ...]
    cells: tuple[CellRecord, ...]
    named_ranges: tuple[NamedRangeRecord, ...] = ()
    external_links: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_uniqueness(self) -> Self:
        sheet_names = [sheet.name for sheet in self.sheets]
        if len(sheet_names) != len(set(sheet_names)):
            raise ValueError("worksheet names must be unique")
        cell_ids = [cell.node_id for cell in self.cells]
        if len(cell_ids) != len(set(cell_ids)):
            raise ValueError("cell records must be unique")
        unknown = sorted({cell.sheet for cell in self.cells} - set(sheet_names))
        if unknown:
            raise ValueError(f"cells refer to unknown sheets: {unknown}")
        return self

    @property
    def sheet_names(self) -> frozenset[str]:
        return frozenset(sheet.name for sheet in self.sheets)

    @property
    def sheet_map(self) -> dict[str, SheetRecord]:
        return {sheet.name: sheet for sheet in self.sheets}

    @property
    def cell_map(self) -> dict[str, CellRecord]:
        return {cell.node_id: cell for cell in self.cells}

    @property
    def named_range_map(self) -> dict[str, tuple[str, ...]]:
        return {item.name: item.destinations for item in self.named_ranges}


MetadataValue = str | int | float | bool | None


class AuditIssue(DomainModel):
    """One evidence-backed workbook finding."""

    code: IssueCode
    severity: Severity
    sheet: str
    cell: str
    title: str
    evidence: str
    recommendation: str
    formula_excerpt: str | None = None
    metadata: dict[str, MetadataValue] = Field(default_factory=dict)

    @property
    def key(self) -> str:
        return f"{self.code}:{self.sheet}!{self.cell}"


class DriftChange(DomainModel):
    """One structural or formula change between workbook versions."""

    kind: DriftKind
    sheet: str
    cell: str | None = None
    before_formula: str | None = None
    after_formula: str | None = None
    before_value_kind: CellValueKind | None = None
    after_value_kind: CellValueKind | None = None


class DriftReport(DomainModel):
    """Deterministic version-comparison result."""

    before_filename: str
    after_filename: str
    before_sha256: str
    after_sha256: str
    changes: tuple[DriftChange, ...]
    summary: dict[DriftKind, int]


class AuditMetrics(DomainModel):
    """Workbook and graph counts that contain no raw cell values."""

    sheet_count: int = Field(ge=0)
    hidden_sheet_count: int = Field(ge=0)
    populated_cell_count: int = Field(ge=0)
    formula_cell_count: int = Field(ge=0)
    named_range_count: int = Field(ge=0)
    merged_range_count: int = Field(ge=0)
    external_link_count: int = Field(ge=0)
    dependency_node_count: int = Field(ge=0)
    dependency_edge_count: int = Field(ge=0)


class AuditReport(DomainModel):
    """Serializable audit result shared by every output adapter."""

    schema_version: str = "1.0"
    tool_version: str
    generated_at: datetime
    source_filename: str
    source_sha256: str
    source_unchanged: bool
    metrics: AuditMetrics
    sheets: tuple[SheetRecord, ...]
    named_ranges: tuple[NamedRangeRecord, ...]
    external_links: tuple[str, ...]
    issues: tuple[AuditIssue, ...]
    issue_summary: dict[IssueCode, int]
    severity_summary: dict[Severity, int]
