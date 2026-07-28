from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parents[2] / "src" / "sheetpilot_beacon" / "app.py"


@pytest.mark.e2e
def test_streamlit_app_exposes_complete_disabled_by_default_workflows() -> None:
    app = AppTest.from_file(str(APP_PATH)).run(timeout=15)

    assert list(app.exception) == []
    assert [tab.label for tab in app.tabs] == [
        "Audit a workbook",
        "Compare versions",
        "Privacy boundary",
    ]
    assert len(app.get("file_uploader")) == 3
    assert [(button.label, button.disabled) for button in app.button] == [
        ("Run offline audit", True),
        ("Compare formula versions", True),
    ]
    rendered_html = "\n".join(markdown.value for markdown in app.markdown)
    assert "Workbook risk,<br>mapped clearly." in rendered_html
    assert "The core makes no network requests and has no telemetry." in rendered_html
