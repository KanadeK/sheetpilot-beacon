from __future__ import annotations

import importlib
import os
import platform
from pathlib import Path

import pytest

import scripts.verify as verify_script
from sheetpilot_beacon.adapters import exporters


def test_polars_cpu_guard_is_scoped_to_hidden_machine_detection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with monkeypatch.context() as patch:
        patch.delenv("POLARS_SKIP_CPU_CHECK", raising=False)
        patch.setattr(platform, "machine", lambda: "")

        reloaded = importlib.reload(exporters)

        assert reloaded._machine_hidden is True
        assert "POLARS_SKIP_CPU_CHECK" not in os.environ
        assert reloaded.pl.DataFrame({"value": [1]}).height == 1

    importlib.reload(exporters)


def test_verifier_places_pytest_temporary_files_inside_worktree(tmp_path: Path) -> None:
    commands = verify_script._commands(tmp_path)
    pytest_command = next(command for command in commands if "pytest" in command)

    assert f"--basetemp={tmp_path}" in pytest_command
