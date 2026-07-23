# Contributing

Thank you for improving SheetPilot Beacon.

## Before opening a change

1. Open an issue for behavior changes that alter risk classifications.
2. Use synthetic workbooks only; never attach confidential business data.
3. Add a regression test for every detector or parser change.
4. Keep the domain core independent from Streamlit and the network.

## Local checks

Use Python 3.12 and run:

```bash
python -m pip install -e ".[dev]"
python scripts/verify.py
```

Commits should be focused and written in the imperative mood. Do not add
generated co-author trailers. By contributing, you agree that your work is
licensed under the MIT License.
