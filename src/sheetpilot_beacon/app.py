"""Local Streamlit interface for SheetPilot Beacon."""

from __future__ import annotations

import streamlit as st

from sheetpilot_beacon.domain.models import AuditReport, DriftKind, DriftReport
from sheetpilot_beacon.ui import UiAuditResult, UiDiffResult, audit_upload, compare_uploads


def _apply_theme() -> None:
    st.markdown(
        """
        <style>
        .stApp { background: #f5f7fa; }
        [data-testid="stHeader"] { background: rgba(245,247,250,.88); }
        .beacon-kicker { color:#0f766e !important; font-weight:800; letter-spacing:.08em;
          text-transform:uppercase; margin-bottom:.4rem; }
        .beacon-hero { font-size:clamp(2.6rem,7vw,5.8rem); line-height:.94;
          letter-spacing:-.055em; color:#102a43 !important; margin:0 0 1rem; }
        .beacon-copy { max-width:740px; color:#52606d !important; font-size:1.08rem; }
        div[data-testid="stMetric"] { background:white; border:1px solid #d9e2ec;
          border-radius:14px; padding:1rem; }
        div[data-testid="stFileUploader"] { background:white; border-radius:14px;
          border:1px solid #d9e2ec; padding:.4rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _issue_rows(report: AuditReport) -> list[dict[str, str]]:
    return [
        {
            "Severity": issue.severity.value,
            "Code": issue.code.value,
            "Location": f"{issue.sheet}!{issue.cell}",
            "Finding": issue.title,
            "Evidence": issue.evidence,
            "Recommendation": issue.recommendation,
        }
        for issue in report.issues
    ]


def _change_rows(report: DriftReport) -> list[dict[str, str]]:
    return [
        {
            "Kind": change.kind.value,
            "Location": f"{change.sheet}!{change.cell}" if change.cell else change.sheet,
            "Before formula": change.before_formula or "",
            "After formula": change.after_formula or "",
            "Before type": change.before_value_kind.value if change.before_value_kind else "",
            "After type": change.after_value_kind.value if change.after_value_kind else "",
        }
        for change in report.changes
    ]


def _render_audit(result: UiAuditResult) -> None:
    report = result.report
    columns = st.columns(4)
    columns[0].metric("Findings", len(report.issues))
    columns[1].metric("Formula cells", report.metrics.formula_cell_count)
    columns[2].metric("Dependency edges", report.metrics.dependency_edge_count)
    columns[3].metric("Hidden sheets", report.metrics.hidden_sheet_count)
    st.caption(
        f"Source SHA-256: `{report.source_sha256}` · "
        f"source unchanged: {'yes' if report.source_unchanged else 'no'}"
    )
    st.dataframe(
        _issue_rows(report),
        width="stretch",
        hide_index=True,
        column_config={
            "Evidence": st.column_config.TextColumn(width="large"),
            "Recommendation": st.column_config.TextColumn(width="large"),
        },
    )
    downloads = st.columns(3)
    stem = report.source_filename.rsplit(".", 1)[0]
    downloads[0].download_button(
        "Download HTML report",
        result.html_report,
        file_name=f"{stem}.audit.html",
        mime="text/html",
        width="stretch",
    )
    downloads[1].download_button(
        "Download JSON evidence",
        result.json_report,
        file_name=f"{stem}.audit.json",
        mime="application/json",
        width="stretch",
    )
    downloads[2].download_button(
        "Download annotated copy",
        result.annotated_xlsx,
        file_name=f"{stem}.annotated.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )


def _render_diff(result: UiDiffResult) -> None:
    report = result.report
    first, second = st.columns(2)
    first.metric("Formula and sheet changes", len(report.changes))
    second.metric(
        "Formula → constant",
        report.summary.get(DriftKind.FORMULA_REPLACED_BY_CONSTANT, 0),
    )
    st.dataframe(_change_rows(report), width="stretch", hide_index=True)
    downloads = st.columns(2)
    downloads[0].download_button(
        "Download drift HTML",
        result.html_report,
        file_name="formula-drift.html",
        mime="text/html",
        width="stretch",
    )
    downloads[1].download_button(
        "Download drift JSON",
        result.json_report,
        file_name="formula-drift.json",
        mime="application/json",
        width="stretch",
    )


def main() -> None:
    st.set_page_config(
        page_title="SheetPilot Beacon",
        page_icon="🔦",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    _apply_theme()
    st.markdown('<p class="beacon-kicker">Offline workbook audit</p>', unsafe_allow_html=True)
    st.markdown(
        '<h1 class="beacon-hero">Workbook risk,<br>mapped clearly.</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="beacon-copy">Find fragile formulas, hidden dependencies, '
        "hardcoded constants, high-impact cells, and formula drift without "
        "uploading data to an external service or changing the original file.</p>",
        unsafe_allow_html=True,
    )
    audit_tab, diff_tab, boundary_tab = st.tabs(
        ("Audit a workbook", "Compare versions", "Privacy boundary")
    )
    with audit_tab:
        upload = st.file_uploader(
            "Choose an Excel workbook",
            type=("xlsx",),
            help="The workbook is processed in this local Streamlit process.",
            key="audit-upload",
        )
        if (
            st.button(
                "Run offline audit",
                type="primary",
                disabled=upload is None,
                width="stretch",
            )
            and upload is not None
        ):
            try:
                st.session_state["audit-result"] = audit_upload(
                    upload.name,
                    upload.getvalue(),
                )
            except (OSError, RuntimeError, ValueError) as error:
                st.error(f"Audit failed: {error}")
        audit_result = st.session_state.get("audit-result")
        if isinstance(audit_result, UiAuditResult):
            _render_audit(audit_result)

    with diff_tab:
        before_column, after_column = st.columns(2)
        before_upload = before_column.file_uploader(
            "Choose the earlier workbook",
            type=("xlsx",),
            key="before-upload",
        )
        after_upload = after_column.file_uploader(
            "Choose the revised workbook",
            type=("xlsx",),
            key="after-upload",
        )
        if (
            st.button(
                "Compare formula versions",
                disabled=before_upload is None or after_upload is None,
                width="stretch",
            )
            and before_upload is not None
            and after_upload is not None
        ):
            try:
                st.session_state["diff-result"] = compare_uploads(
                    before_upload.name,
                    before_upload.getvalue(),
                    after_upload.name,
                    after_upload.getvalue(),
                )
            except (OSError, RuntimeError, ValueError) as error:
                st.error(f"Comparison failed: {error}")
        diff_result = st.session_state.get("diff-result")
        if isinstance(diff_result, UiDiffResult):
            _render_diff(diff_result)

    with boundary_tab:
        st.subheader("What stays private")
        st.markdown(
            """
            - The core makes no network requests and has no telemetry.
            - Reports omit raw cell values and redact credential-shaped formula text.
            - Annotated output is a new workbook copy; the source is never saved.
            - Static analysis checks structure and formula text; it does not execute macros
              or claim calculated-value correctness.
            """
        )


if __name__ == "__main__":
    main()
