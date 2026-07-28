from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pytest

from scripts import package_release, release_check


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_static_demo_archive_is_deterministic_and_contains_only_reports(
    tmp_path: Path,
) -> None:
    demo = tmp_path / "demo"
    demo.mkdir()
    (demo / "index.html").write_text("<h1>index</h1>", encoding="utf-8")
    (demo / "budget.audit.html").write_text("<h1>report</h1>", encoding="utf-8")
    (demo / "budget.audit.json").write_text('{"issues":[]}', encoding="utf-8")
    (demo / "budget.annotated.xlsx").write_bytes(b"excluded workbook")
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"

    package_release._write_static_demo_zip(demo, first)
    package_release._write_static_demo_zip(demo, second)

    assert _sha256(first) == _sha256(second)
    with zipfile.ZipFile(first) as bundle:
        assert sorted(Path(name).suffix for name in bundle.namelist()) == [
            ".html",
            ".html",
            ".json",
        ]


def test_checksum_manifest_covers_every_asset_and_changes_after_tamper(
    tmp_path: Path,
) -> None:
    first = tmp_path / "one.txt"
    second = tmp_path / "two.txt"
    first.write_text("one", encoding="utf-8")
    second.write_text("two", encoding="utf-8")

    manifest = package_release._write_checksums(tmp_path)
    before = manifest.read_text(encoding="utf-8")
    first.write_text("changed", encoding="utf-8")
    package_release._write_checksums(tmp_path)
    after = manifest.read_text(encoding="utf-8")

    assert "one.txt" in before and "two.txt" in before
    assert before != after


def test_release_metadata_matches_current_version() -> None:
    release_check._check_versions()

    assert release_check._expected_assets() == {
        "sheetpilot_beacon-0.1.0-py3-none-any.whl",
        "sheetpilot_beacon-0.1.0.tar.gz",
        "sheetpilot-beacon-0.1.0-example-budget_model.xlsx",
        "sheetpilot-beacon-0.1.0-example-engineering_boq.xlsx",
        "sheetpilot-beacon-0.1.0-example-sales_forecast.xlsx",
        "sheetpilot-beacon-0.1.0-static-report.html",
        "sheetpilot-beacon-0.1.0-static-demo.zip",
        "sheetpilot-beacon-0.1.0-install-smoke.json",
        "SHA256SUMS.txt",
    }


def test_release_metadata_accepts_a_branch_ref(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_REF_TYPE", "branch")
    monkeypatch.setenv("GITHUB_REF_NAME", "main")

    release_check._check_versions()


def test_release_metadata_rejects_a_mismatched_tag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_REF_TYPE", "tag")
    monkeypatch.setenv("GITHUB_REF_NAME", "v9.9.9")

    with pytest.raises(RuntimeError, match=r"tag v9\.9\.9 does not match v0\.1\.0"):
        release_check._check_versions()


def test_release_text_and_python_body_checks_pass_repository_sources() -> None:
    release_check._check_forbidden_text()
    release_check._check_python_bodies()


def test_release_asset_check_rejects_missing_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(release_check, "RELEASE_DIRECTORY", tmp_path / "missing")

    with pytest.raises(RuntimeError, match="does not exist"):
        release_check._check_assets()
