# Demo and visual evidence

## Static report demo

Generate the three-workbook static demo:

```bash
python scripts/demo.py
```

The command writes `demo-output/index.html`, three audit HTML reports, three
JSON reports, and three annotated workbook copies. Every result comes from the
same core used by the CLI and Streamlit interface.

GitHub Pages deploys only the generated static index and audit reports from the
MIT-licensed synthetic samples. It contains no upload endpoint, workbook from a
user, token, or environment file.

## Interface screenshot

Install the Playwright browser runtime once:

```bash
python -m playwright install chromium
```

Then run:

```bash
python scripts/capture_demo.py
```

The script starts Streamlit on an available local port, waits for the health
endpoint, uploads `examples/budget_model.xlsx`, runs the audit, verifies the
HTML download control, and writes
`docs/assets/sheetpilot-beacon-ui.png`.

The checked-in screenshot was generated with this path and visually reviewed at
desktop width. The same interface was manually exercised at 390×844: upload,
metrics, tabs, and download controls remained reachable without horizontal
page overflow.
