"""Byte-oriented helpers shared by Streamlit and UI tests."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from sheetpilot_beacon.adapters.exporters import (
    export_annotated_workbook,
    export_drift_html,
    export_drift_json,
    export_html_report,
    export_json_report,
)
from sheetpilot_beacon.domain.detectors import DetectorConfig
from sheetpilot_beacon.domain.models import AuditReport, DriftReport
from sheetpilot_beacon.services.audit import Clock, audit_workbook
from sheetpilot_beacon.services.diff import compare_workbooks

MAX_UPLOAD_BYTES = 100 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class UiAuditResult:
    report: AuditReport
    json_report: bytes
    html_report: bytes
    annotated_xlsx: bytes


@dataclass(frozen=True, slots=True)
class UiDiffResult:
    report: DriftReport
    json_report: bytes
    html_report: bytes


def safe_upload_name(filename: str) -> str:
    """Return a basename-only `.xlsx` name safe for a temporary directory."""

    normalized = filename.replace("\\", "/")
    candidate = normalized.rsplit("/", 1)[-1].strip()
    if (
        not candidate
        or candidate.casefold() == ".xlsx"
        or Path(candidate).suffix.casefold() != ".xlsx"
    ):
        raise ValueError("upload must have a non-empty .xlsx filename")
    return candidate


def _validate_payload(payload: bytes) -> None:
    if not payload:
        raise ValueError("uploaded workbook is empty")
    if len(payload) > MAX_UPLOAD_BYTES:
        raise ValueError(f"uploaded workbook exceeds {MAX_UPLOAD_BYTES} bytes")


def audit_upload(
    filename: str,
    payload: bytes,
    *,
    detector_config: DetectorConfig | None = None,
    clock: Clock | None = None,
    work_dir: Path | None = None,
) -> UiAuditResult:
    """Audit uploaded bytes and return complete download artifacts."""

    safe_name = safe_upload_name(filename)
    _validate_payload(payload)
    if work_dir is not None:
        work_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="sheetpilot-audit-",
        dir=work_dir,
    ) as temporary:
        root = Path(temporary)
        source = root / safe_name
        source.write_bytes(payload)
        report = audit_workbook(
            source,
            detector_config=detector_config,
            clock=clock,
        )
        stem = Path(safe_name).stem
        json_path = export_json_report(report, root / f"{stem}.audit.json")
        html_path = export_html_report(report, root / f"{stem}.audit.html")
        annotated_path = export_annotated_workbook(
            source,
            report,
            root / f"{stem}.annotated.xlsx",
        )
        return UiAuditResult(
            report=report,
            json_report=json_path.read_bytes(),
            html_report=html_path.read_bytes(),
            annotated_xlsx=annotated_path.read_bytes(),
        )


def compare_uploads(
    before_filename: str,
    before_payload: bytes,
    after_filename: str,
    after_payload: bytes,
    *,
    work_dir: Path | None = None,
) -> UiDiffResult:
    """Compare two uploaded workbooks and return downloadable reports."""

    before_name = safe_upload_name(before_filename)
    after_name = safe_upload_name(after_filename)
    _validate_payload(before_payload)
    _validate_payload(after_payload)
    if work_dir is not None:
        work_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="sheetpilot-diff-",
        dir=work_dir,
    ) as temporary:
        root = Path(temporary)
        before = root / "before" / before_name
        after = root / "after" / after_name
        before.parent.mkdir()
        after.parent.mkdir()
        before.write_bytes(before_payload)
        after.write_bytes(after_payload)
        report = compare_workbooks(before, after)
        json_path = export_drift_json(report, root / "formula-drift.json")
        html_path = export_drift_html(report, root / "formula-drift.html")
        return UiDiffResult(
            report=report,
            json_report=json_path.read_bytes(),
            html_report=html_path.read_bytes(),
        )
