from __future__ import annotations

import json
from pathlib import Path

import openpyxl
import pytest

from sheetpilot_beacon.adapters.samples import generate_sample_workbooks
from sheetpilot_beacon.cli import severity_exit_code
from sheetpilot_beacon.domain.models import DriftKind, Severity
from sheetpilot_beacon.ui import audit_upload, compare_uploads, safe_upload_name


@pytest.mark.parametrize(
    ("candidate", "expected"),
    [
        ("budget.xlsx", "budget.xlsx"),
        ("../../budget.xlsx", "budget.xlsx"),
        (r"C:\private\forecast.xlsx", "forecast.xlsx"),
    ],
)
def test_safe_upload_name_removes_path_components(
    candidate: str,
    expected: str,
) -> None:
    assert safe_upload_name(candidate) == expected


@pytest.mark.parametrize("candidate", ["", "book.xls", "book.csv", ".xlsx"])
def test_safe_upload_name_rejects_unsupported_names(candidate: str) -> None:
    with pytest.raises(ValueError):
        safe_upload_name(candidate)


def test_severity_exit_code_honors_fail_threshold() -> None:
    assert severity_exit_code((Severity.MEDIUM,), fail_on=None) == 0
    assert severity_exit_code((Severity.MEDIUM,), fail_on=Severity.HIGH) == 0
    assert severity_exit_code((Severity.MEDIUM,), fail_on=Severity.MEDIUM) == 3
    assert severity_exit_code((Severity.CRITICAL,), fail_on=Severity.HIGH) == 3


@pytest.mark.integration
def test_upload_audit_returns_downloadable_real_artifacts(tmp_path: Path) -> None:
    source = generate_sample_workbooks(tmp_path / "source")["budget_model.xlsx"]

    result = audit_upload(
        "budget_model.xlsx",
        source.read_bytes(),
        work_dir=tmp_path / "ui",
    )

    assert len(result.report.issues) == 5
    assert result.annotated_xlsx.startswith(b"PK")
    assert b"<!doctype html>" in result.html_report
    assert json.loads(result.json_report)["source_filename"] == "budget_model.xlsx"


@pytest.mark.integration
def test_upload_comparison_locates_formula_replaced_by_constant(tmp_path: Path) -> None:
    before = generate_sample_workbooks(tmp_path / "source")["budget_model.xlsx"]
    after = tmp_path / "budget_model_revised.xlsx"
    workbook = openpyxl.load_workbook(before, data_only=False)
    try:
        workbook["Budget"]["C6"] = 121.0
        workbook.save(after)
    finally:
        workbook.close()

    result = compare_uploads(
        before.name,
        before.read_bytes(),
        after.name,
        after.read_bytes(),
        work_dir=tmp_path / "ui",
    )

    assert any(
        change.kind is DriftKind.FORMULA_REPLACED_BY_CONSTANT
        and change.sheet == "Budget"
        and change.cell == "C6"
        for change in result.report.changes
    )
    assert b"formula_replaced_by_constant" in result.html_report
    assert json.loads(result.json_report)["after_filename"] == after.name
