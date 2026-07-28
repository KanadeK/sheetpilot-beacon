# Benchmark

This benchmark measures the deterministic core audit over the three committed
synthetic workbooks. It excludes process startup, package installation,
Streamlit rendering, and export writing.

## Reproduce

```bash
python scripts/benchmark.py --iterations 20 --json
```

The script performs one warmup per workbook, then 20 measured audits per
workbook using `time.perf_counter`.

## Measured environment

- Date: 2026-07-28
- Python: 3.12.13
- OS: Windows 11, build 26200, 64-bit
- Machine: AMD64
- Processor reported by Python: Intel64 Family 6 Model 183 Stepping 1
- Package: editable `sheetpilot-beacon` 0.1.0

## Results

| Workbook | Bytes | Formula cells | Findings | Median | p95 | Maximum |
|---|---:|---:|---:|---:|---:|---:|
| `budget_model.xlsx` | 11,378 | 18 | 5 | 27.685 ms | 36.635 ms | 52.641 ms |
| `engineering_boq.xlsx` | 11,379 | 18 | 5 | 24.832 ms | 39.215 ms | 48.100 ms |
| `sales_forecast.xlsx` | 11,362 | 18 | 5 | 28.972 ms | 40.792 ms | 71.278 ms |

All 60 measured runs returned the expected five findings per workbook.

## Interpretation

The committed sample scale completes in tens of milliseconds on this machine.
These measurements are evidence for this environment and input size, not a
cross-machine performance guarantee. Large sparse worksheet extents, long
formulas, dense range references, external-link metadata, antivirus scanning,
and storage speed can materially change runtime.
