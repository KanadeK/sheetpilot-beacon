# Contributing

Thank you for improving SheetPilot Beacon.

## Ground rules

1. Use synthetic workbooks only. Never commit or attach confidential business
   data, customer files, tokens, personal data, or internal paths.
2. Open an issue before changing detector semantics or severity.
3. Keep the domain core independent of Streamlit and the network.
4. Add a regression test for every parser, detector, privacy, or platform fix.
5. Preserve source non-modification and report data-minimization guarantees.

## Development setup

Use Python 3.12:

```bash
git clone https://github.com/KanadeK/sheetpilot-beacon.git
cd sheetpilot-beacon
python -m venv .venv
python -m pip install -e ".[dev]"
python scripts/verify.py
```

uv users can reproduce the lockfile:

```bash
uv sync --frozen --all-extras
```

## Tests

- Pure parser, detector, graph, and model behavior belongs in `tests/unit`.
- Real `.xlsx` reads and exports belong in `tests/integration`.
- Complete commands and application workflows belong in `tests/e2e`.
- Use `FixedClock` for time assertions.
- Assert exact finding code and location rather than only issue count.
- Test both missed findings and unexpected findings for sample changes.

Run a focused test first, then the complete gate:

```bash
python -m pytest tests/unit/test_domain_core.py -q
python scripts/verify.py
```

Coverage must remain at least 80% overall; critical domain modules should remain
near or above 90%.

## Synthetic workbook changes

Generate samples through `sheetpilot_beacon.adapters.samples`, not by embedding
opaque binary fixtures from another source:

```bash
python scripts/generate_samples.py
```

Update `examples/expected_findings.json` only when the intended detector
contract changes, and explain the decision in the pull request.

## Style and commits

- Ruff owns formatting and lint.
- Mypy runs in strict mode for `src`.
- Keep commits focused and use imperative subjects.
- Do not add generated `Co-authored-by` trailers.
- Do not weaken a failing gate to make a change pass.

## Pull requests

Complete the pull request template. Include the failure reproduced, the chosen
behavior, tests added, privacy impact, and exact commands run. Screenshots must
come from the running application and use synthetic samples.

By contributing, you agree that your work is licensed under the MIT License.
