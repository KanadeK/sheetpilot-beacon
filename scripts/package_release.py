"""Build, install-smoke, and checksum the complete v0.1.0 release bundle."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import venv
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from sheetpilot_beacon import __version__
from sheetpilot_beacon.services.audit import FixedClock
from sheetpilot_beacon.services.demo import run_demo


def _repository_root() -> Path:
    working_directory = Path.cwd()
    if (working_directory / "pyproject.toml").is_file():
        return working_directory
    return Path(__file__).resolve().parents[1]


REPOSITORY_ROOT = _repository_root()
RELEASE_DIRECTORY = REPOSITORY_ROOT / "dist-release"
PROJECT_SLUG = "sheetpilot-beacon"
RELEASE_CLOCK = datetime(2026, 7, 28, tzinfo=UTC)
SOURCE_DATE_EPOCH = str(int(RELEASE_CLOCK.timestamp()))
SAMPLE_NAMES = (
    "budget_model.xlsx",
    "engineering_boq.xlsx",
    "sales_forecast.xlsx",
)


def _repository_command_cwd() -> Path | None:
    return None if (Path.cwd() / ".git").is_dir() else REPOSITORY_ROOT


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _recreate_release_directory() -> None:
    root = REPOSITORY_ROOT.resolve()
    target = RELEASE_DIRECTORY.resolve()
    if target.parent != root or target.name != "dist-release":
        raise RuntimeError(f"refusing to replace unexpected release path: {target}")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir()


def _build_distributions(staging: Path) -> tuple[Path, Path]:
    build_output = staging / "distributions"
    build_output.mkdir()
    environment = os.environ.copy()
    environment["SOURCE_DATE_EPOCH"] = SOURCE_DATE_EPOCH
    subprocess.run(
        (
            sys.executable,
            "-m",
            "build",
            "--outdir",
            str(build_output),
        ),
        cwd=_repository_command_cwd(),
        env=environment,
        check=True,
    )
    wheels = tuple(build_output.glob(f"sheetpilot_beacon-{__version__}-*.whl"))
    sdists = tuple(build_output.glob(f"sheetpilot_beacon-{__version__}.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise RuntimeError(
            f"expected one wheel and one sdist, found {len(wheels)} and {len(sdists)}"
        )
    return wheels[0], sdists[0]


def _write_static_demo_zip(demo_root: Path, output: Path) -> None:
    selected = sorted(
        path
        for path in demo_root.iterdir()
        if path.name == "index.html" or path.suffix in {".html", ".json"}
    )
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in selected:
            archive_name = f"{PROJECT_SLUG}-{__version__}-static-demo/{path.name}"
            entry = zipfile.ZipInfo(
                archive_name,
                date_time=(
                    RELEASE_CLOCK.year,
                    RELEASE_CLOCK.month,
                    RELEASE_CLOCK.day,
                    0,
                    0,
                    0,
                ),
            )
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            bundle.writestr(entry, path.read_bytes())


def _venv_python(environment: Path) -> Path:
    if os.name == "nt":
        return environment / "Scripts" / "python.exe"
    return environment / "bin" / "python"


def _install_smoke(wheel: Path, sample: Path, staging: Path) -> dict[str, object]:
    environment = staging / "clean-install"
    venv.EnvBuilder(with_pip=True, clear=True).create(environment)
    python = _venv_python(environment)
    subprocess.run(
        (
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            str(wheel),
        ),
        cwd=staging,
        check=True,
    )
    version = subprocess.run(
        (str(python), "-m", "sheetpilot_beacon.cli", "--version"),
        cwd=staging,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    smoke_output = staging / "install-smoke-output"
    completed = subprocess.run(
        (
            str(python),
            "-m",
            "sheetpilot_beacon.cli",
            "scan",
            str(sample),
            "--output-dir",
            str(smoke_output),
        ),
        cwd=staging,
        check=True,
        capture_output=True,
        text=True,
    )
    report_path = smoke_output / "budget_model.audit.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if (
        version != __version__
        or len(report["issues"]) != 5
        or report["source_unchanged"] is not True
    ):
        raise RuntimeError("clean-install smoke result did not match the release contract")
    scan_summary = completed.stdout.strip().splitlines()[0]
    return {
        "tool_version": version,
        "wheel": wheel.name,
        "command": "sheetpilot scan budget_model.xlsx",
        "scan_summary": scan_summary,
        "source_sha256": report["source_sha256"],
        "source_unchanged": report["source_unchanged"],
        "findings": len(report["issues"]),
        "formula_cells": report["metrics"]["formula_cell_count"],
        "dependency_edges": report["metrics"]["dependency_edge_count"],
    }


def _write_checksums(directory: Path) -> Path:
    assets = sorted(path for path in directory.iterdir() if path.name != "SHA256SUMS.txt")
    checksums = directory / "SHA256SUMS.txt"
    checksums.write_text(
        "".join(f"{_sha256(path)}  {path.name}\n" for path in assets),
        encoding="utf-8",
        newline="\n",
    )
    return checksums


def package_release() -> tuple[Path, ...]:
    """Create and validate every release asset."""

    _recreate_release_directory()
    build_root = REPOSITORY_ROOT / "build"
    build_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="release-", dir=build_root) as temporary:
        staging = Path(temporary)
        wheel, sdist = _build_distributions(staging)
        release_wheel = RELEASE_DIRECTORY / wheel.name
        release_sdist = RELEASE_DIRECTORY / sdist.name
        shutil.copy2(wheel, release_wheel)
        shutil.copy2(sdist, release_sdist)

        for sample_name in SAMPLE_NAMES:
            source = REPOSITORY_ROOT / "examples" / sample_name
            destination = RELEASE_DIRECTORY / (
                f"{PROJECT_SLUG}-{__version__}-example-{sample_name}"
            )
            shutil.copy2(source, destination)

        demo_root = staging / "static-demo"
        run_demo(
            REPOSITORY_ROOT / "examples",
            demo_root,
            clock=FixedClock(RELEASE_CLOCK),
        )
        static_report = RELEASE_DIRECTORY / (f"{PROJECT_SLUG}-{__version__}-static-report.html")
        shutil.copy2(demo_root / "budget_model.audit.html", static_report)
        static_demo = RELEASE_DIRECTORY / (f"{PROJECT_SLUG}-{__version__}-static-demo.zip")
        _write_static_demo_zip(demo_root, static_demo)

        smoke = _install_smoke(
            release_wheel,
            REPOSITORY_ROOT / "examples" / "budget_model.xlsx",
            staging,
        )
        smoke_path = RELEASE_DIRECTORY / (f"{PROJECT_SLUG}-{__version__}-install-smoke.json")
        smoke_path.write_text(
            json.dumps(smoke, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    _write_checksums(RELEASE_DIRECTORY)
    return tuple(sorted(RELEASE_DIRECTORY.iterdir()))


def main() -> int:
    assets = package_release()
    print(f"Release bundle: {RELEASE_DIRECTORY}")
    for asset in assets:
        print(f"{asset.name}: {asset.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
