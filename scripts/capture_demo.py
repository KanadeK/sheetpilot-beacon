"""Capture the real Streamlit audit result used by the README."""

from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import expect, sync_playwright

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = REPOSITORY_ROOT / "src" / "sheetpilot_beacon" / "app.py"


def _available_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _wait_for_health(url: str, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError) as error:
            last_error = error
        time.sleep(0.1)
    raise RuntimeError(f"Streamlit did not become healthy: {last_error}")


def capture(sample: Path, output: Path) -> None:
    """Start the local UI, audit a sample, and capture the rendered result."""

    port = _available_port()
    command = (
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(APP_PATH),
        "--server.address",
        "127.0.0.1",
        "--server.port",
        str(port),
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    )
    server = subprocess.Popen(
        command,
        cwd=REPOSITORY_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    try:
        _wait_for_health(f"http://127.0.0.1:{port}/_stcore/health")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={"width": 1440, "height": 900})
                page.goto(f"http://127.0.0.1:{port}", wait_until="networkidle")
                uploaders = page.locator('input[type="file"]')
                expect(uploaders).to_have_count(3)
                uploaders.nth(0).set_input_files(sample)
                audit = page.get_by_role("button", name="Run offline audit")
                expect(audit).to_be_enabled()
                audit.click()
                expect(page.get_by_text("Findings", exact=True)).to_be_visible(timeout=30_000)
                expect(page.get_by_role("button", name="Download HTML report")).to_be_visible()
                output.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=output, full_page=True)
            finally:
                browser.close()
    except PlaywrightError as error:
        raise RuntimeError(
            "Playwright Chromium is unavailable. Run "
            "`python -m playwright install chromium` once, then retry."
        ) from error
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sample",
        type=Path,
        default=REPOSITORY_ROOT / "examples" / "budget_model.xlsx",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPOSITORY_ROOT / "docs" / "assets" / "sheetpilot-beacon-ui.png",
    )
    arguments = parser.parse_args()
    capture(arguments.sample.resolve(), arguments.output.resolve())
    print(arguments.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
