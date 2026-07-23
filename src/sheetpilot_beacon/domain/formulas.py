"""Formula token parsing and copy-pattern normalization."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

from openpyxl.formula import Tokenizer
from openpyxl.formula.translate import Translator
from openpyxl.utils.cell import get_column_letter, range_boundaries

CELL_OR_RANGE = re.compile(
    r"^\$?[A-Za-z]{1,3}\$?[1-9][0-9]*"
    r"(?::\$?[A-Za-z]{1,3}\$?[1-9][0-9]*)?$"
)
EXTERNAL_QUALIFIER = re.compile(r"^\[(?P<book>[^\]]+)\](?P<sheet>.+)$")


@dataclass(frozen=True, slots=True)
class FormulaReference:
    """One internal cell, external cell, or bounded symbolic range reference."""

    sheet: str
    coordinate: str
    token: str
    external_book: str | None = None
    named_range: str | None = None
    is_symbolic_range: bool = False

    @property
    def node_id(self) -> str:
        prefix = (
            f"external:[{self.external_book}]{self.sheet}" if self.external_book else self.sheet
        )
        return f"{prefix}!{self.coordinate}"


def _clean_qualifier(qualifier: str) -> tuple[str, str | None]:
    cleaned = qualifier.strip()
    if cleaned.startswith("'") and cleaned.endswith("'"):
        cleaned = cleaned[1:-1].replace("''", "'")
    external = EXTERNAL_QUALIFIER.fullmatch(cleaned)
    if external:
        return external.group("sheet"), external.group("book")
    return cleaned, None


def _normalize_address(address: str) -> str:
    return address.replace("$", "").upper()


def _expand_address(
    *,
    sheet: str,
    address: str,
    token: str,
    external_book: str | None,
    max_range_cells: int,
) -> list[FormulaReference]:
    normalized = _normalize_address(address)
    if ":" not in normalized:
        return [
            FormulaReference(
                sheet=sheet,
                coordinate=normalized,
                token=token,
                external_book=external_book,
            )
        ]
    min_column, min_row, max_column, max_row = range_boundaries(normalized)
    cell_count = (max_column - min_column + 1) * (max_row - min_row + 1)
    if cell_count > max_range_cells:
        return [
            FormulaReference(
                sheet=sheet,
                coordinate=normalized,
                token=token,
                external_book=external_book,
                is_symbolic_range=True,
            )
        ]
    return [
        FormulaReference(
            sheet=sheet,
            coordinate=f"{get_column_letter(column)}{row}",
            token=token,
            external_book=external_book,
        )
        for row in range(min_row, max_row + 1)
        for column in range(min_column, max_column + 1)
    ]


def _parse_operand(
    operand: str,
    *,
    current_sheet: str,
    named_ranges: dict[str, tuple[str, ...]],
    max_range_cells: int,
    seen_names: frozenset[str],
) -> list[FormulaReference]:
    token = operand.strip()
    if token in named_ranges and token not in seen_names:
        references: list[FormulaReference] = []
        for destination in named_ranges[token]:
            parsed = _parse_operand(
                destination,
                current_sheet=current_sheet,
                named_ranges=named_ranges,
                max_range_cells=max_range_cells,
                seen_names=seen_names | {token},
            )
            references.extend(replace(reference, named_range=token) for reference in parsed)
        return references

    if "!" in token:
        qualifier, address = token.rsplit("!", 1)
        sheet, external_book = _clean_qualifier(qualifier)
    else:
        address = token
        sheet = current_sheet
        external_book = None
    if not CELL_OR_RANGE.fullmatch(address):
        return []
    try:
        return _expand_address(
            sheet=sheet,
            address=address,
            token=token,
            external_book=external_book,
            max_range_cells=max_range_cells,
        )
    except ValueError:
        return []


def parse_formula_references(
    formula: str,
    *,
    current_sheet: str,
    named_ranges: dict[str, tuple[str, ...]] | None = None,
    max_range_cells: int = 10_000,
) -> tuple[FormulaReference, ...]:
    """Resolve A1, sheet-qualified, named, and external formula operands."""

    if not formula.startswith("="):
        raise ValueError("formula must begin with '='")
    if max_range_cells < 1:
        raise ValueError("max_range_cells must be positive")
    names = named_ranges or {}
    try:
        tokens = Tokenizer(formula).items
    except (IndexError, TypeError, ValueError):
        return ()
    references: dict[str, FormulaReference] = {}
    for item in tokens:
        if item.type != "OPERAND" or item.subtype != "RANGE":
            continue
        for reference in _parse_operand(
            item.value,
            current_sheet=current_sheet,
            named_ranges=names,
            max_range_cells=max_range_cells,
            seen_names=frozenset(),
        ):
            references.setdefault(reference.node_id, reference)
    return tuple(references.values())


def canonical_formula(formula: str, *, origin: str) -> str:
    """Translate copy-equivalent formulas to a shared safe anchor."""

    if not formula.startswith("="):
        raise ValueError("formula must begin with '='")
    try:
        translated = Translator(formula, origin=origin).translate_formula("ZZ1000")
    except (IndexError, TypeError, ValueError):
        translated = formula
    return re.sub(r"\s+", "", translated).upper()
