"""Enforce the complete local v0.1.0 publication gate."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

from sheetpilot_beacon import __version__


def _repository_root() -> Path:
    working_directory = Path.cwd()
    if (working_directory / "pyproject.toml").is_file():
        return working_directory
    return Path(__file__).resolve().parents[1]


REPOSITORY_ROOT = _repository_root()
RELEASE_DIRECTORY = REPOSITORY_ROOT / "dist-release"
PROJECT_SLUG = "sheetpilot-beacon"
FORBIDDEN_MARKERS = (
    "TO" + "DO",
    "FIX" + "ME",
    "Not" + "Implemented",
    "place" + "holder",
    "coming" + " soon",
    "lorem" + " ipsum",
)
BINARY_SUFFIXES = {".gif", ".jpg", ".jpeg", ".pdf", ".png", ".webp", ".whl", ".xlsx"}


def _repository_command_cwd() -> Path | None:
    return None if (Path.cwd() / ".git").is_dir() else REPOSITORY_ROOT


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git(*arguments: str) -> str:
    # The desktop sandbox and the interactive Windows account have distinct
    # SIDs. Scope trust to this read-only Git subprocess instead of changing
    # the user's global safe.directory configuration.
    return subprocess.run(
        ("git", "-c", "safe.directory=*", *arguments),
        cwd=_repository_command_cwd(),
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _tracked_files() -> list[Path]:
    return [REPOSITORY_ROOT / line for line in _git("ls-files").splitlines() if line]


def _check_worktree() -> None:
    status = _git("status", "--porcelain", "--untracked-files=all").strip()
    if status:
        raise RuntimeError(f"worktree is not clean:\n{status}")


def _check_versions() -> None:
    pyproject = tomllib.loads((REPOSITORY_ROOT / "pyproject.toml").read_text("utf-8"))
    project_version = str(pyproject["project"]["version"])
    if project_version != __version__:
        raise RuntimeError(f"version mismatch: pyproject={project_version}, package={__version__}")
    expected_heading = f"## [{__version__}]"
    changelog = (REPOSITORY_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if expected_heading not in changelog:
        raise RuntimeError(f"CHANGELOG lacks {expected_heading}")
    for readme in ("README.md", "README.zh-CN.md"):
        if f"v{__version__}" not in (REPOSITORY_ROOT / readme).read_text("utf-8"):
            raise RuntimeError(f"{readme} lacks v{__version__}")
    tag = os.environ.get("GITHUB_REF_NAME")
    if os.environ.get("GITHUB_REF_TYPE") == "tag" and tag != f"v{__version__}":
        raise RuntimeError(f"tag {tag} does not match v{__version__}")


def _check_authors() -> None:
    expected = ("KanadeK", "121669563+KanadeK@users.noreply.github.com")
    rows = _git("log", "--format=%an%x1f%ae%x1f%cn%x1f%ce").splitlines()
    for row in rows:
        author_name, author_email, committer_name, committer_email = row.split("\x1f")
        if (author_name, author_email) != expected:
            raise RuntimeError(f"unexpected author: {author_name} <{author_email}>")
        if (committer_name, committer_email) != expected:
            raise RuntimeError(f"unexpected committer: {committer_name} <{committer_email}>")
    if "co-authored-by:" in _git("log", "--format=%B").casefold():
        raise RuntimeError("commit history contains a co-author trailer")


def _check_forbidden_text() -> None:
    lowered_markers = tuple(marker.casefold() for marker in FORBIDDEN_MARKERS)
    findings: list[str] = []
    for path in _tracked_files():
        if path.suffix.casefold() in BINARY_SUFFIXES:
            continue
        text = path.read_bytes().decode("utf-8", errors="replace").casefold()
        for marker in lowered_markers:
            if marker in text:
                findings.append(f"{path.relative_to(REPOSITORY_ROOT)}: {marker}")
    if findings:
        raise RuntimeError("forbidden shell markers found:\n" + "\n".join(findings))


def _check_python_bodies() -> None:
    findings: list[str] = []
    for path in _tracked_files():
        if path.suffix != ".py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            body = node.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                body = body[1:]
            if len(body) == 1 and isinstance(body[0], ast.Pass):
                findings.append(f"{path.relative_to(REPOSITORY_ROOT)}:{node.lineno}")
            if (
                len(body) == 1
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and body[0].value.value is Ellipsis
            ):
                findings.append(f"{path.relative_to(REPOSITORY_ROOT)}:{node.lineno}")
    if findings:
        raise RuntimeError("empty Python bodies found:\n" + "\n".join(findings))


def _expected_assets() -> set[str]:
    sample_assets = {
        f"{PROJECT_SLUG}-{__version__}-example-{name}"
        for name in (
            "budget_model.xlsx",
            "engineering_boq.xlsx",
            "sales_forecast.xlsx",
        )
    }
    return {
        f"sheetpilot_beacon-{__version__}-py3-none-any.whl",
        f"sheetpilot_beacon-{__version__}.tar.gz",
        *sample_assets,
        f"{PROJECT_SLUG}-{__version__}-static-report.html",
        f"{PROJECT_SLUG}-{__version__}-static-demo.zip",
        f"{PROJECT_SLUG}-{__version__}-install-smoke.json",
        "SHA256SUMS.txt",
    }


def _check_assets() -> None:
    if not RELEASE_DIRECTORY.is_dir():
        raise RuntimeError("dist-release does not exist; run package_release.py")
    observed = {path.name for path in RELEASE_DIRECTORY.iterdir() if path.is_file()}
    expected = _expected_assets()
    if observed != expected:
        raise RuntimeError(
            f"release assets differ: missing={sorted(expected - observed)}, "
            f"extra={sorted(observed - expected)}"
        )

    checksum_path = RELEASE_DIRECTORY / "SHA256SUMS.txt"
    recorded: dict[str, str] = {}
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        checksum, name = line.split("  ", 1)
        recorded[name] = checksum
    asset_names = expected - {"SHA256SUMS.txt"}
    if set(recorded) != asset_names:
        raise RuntimeError("SHA256SUMS does not enumerate every release asset")
    for name, checksum in recorded.items():
        if _sha256(RELEASE_DIRECTORY / name) != checksum:
            raise RuntimeError(f"checksum mismatch: {name}")

    smoke_path = RELEASE_DIRECTORY / (f"{PROJECT_SLUG}-{__version__}-install-smoke.json")
    smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
    if (
        smoke["tool_version"] != __version__
        or smoke["findings"] != 5
        or smoke["source_unchanged"] is not True
        or smoke["scan_summary"]
        != "budget_model.xlsx: 5 findings, 18 formulas, 19 dependency edges"
    ):
        raise RuntimeError("install-smoke evidence does not match the release contract")

    report_path = RELEASE_DIRECTORY / (f"{PROJECT_SLUG}-{__version__}-static-report.html")
    report = report_path.read_text(encoding="utf-8")
    if "Findings (5)" not in report or "source unchanged:" not in report:
        raise RuntimeError("static report lacks expected audit evidence")

    demo_path = RELEASE_DIRECTORY / f"{PROJECT_SLUG}-{__version__}-static-demo.zip"
    with zipfile.ZipFile(demo_path) as bundle:
        names = bundle.namelist()
        if len(names) != 7 or not any(name.endswith("/index.html") for name in names):
            raise RuntimeError("static demo archive has an unexpected manifest")
        if any(Path(name).is_absolute() or ".." in Path(name).parts for name in names):
            raise RuntimeError("static demo archive contains an unsafe path")


def _run_verification() -> None:
    subprocess.run(
        (sys.executable, "scripts/verify.py"),
        cwd=_repository_command_cwd(),
        check=True,
    )
    subprocess.run(
        (sys.executable, "scripts/secret_scan.py"),
        cwd=_repository_command_cwd(),
        check=True,
    )


def main() -> int:
    checks = (
        ("clean worktree", _check_worktree),
        ("version consistency", _check_versions),
        ("author and committer identity", _check_authors),
        ("forbidden text", _check_forbidden_text),
        ("non-empty Python bodies", _check_python_bodies),
        ("release assets and checksums", _check_assets),
        ("tests, typing, builds, and secrets", _run_verification),
        ("clean worktree after verification", _check_worktree),
    )
    for label, check in checks:
        check()
        print(f"PASS: {label}")
    print(f"Release gate passed for v{__version__}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
