# Architecture

SheetPilot Beacon separates workbook I/O from deterministic audit logic.

```text
CLI / Streamlit
       |
services (audit, diff, export orchestration)
       |
domain (models, formula references, graph, detectors, drift)
       |
adapters (openpyxl reader/writer, HTML and JSON output)
```

## Boundaries

- `domain` owns typed snapshots, dependency construction, detector policies,
  severity, and version-diff semantics. It does not import Streamlit.
- `adapters` translate `.xlsx` packages and report formats without deciding
  which findings are valid.
- `services` verify input hashes, assemble reports, and coordinate exports.
- `cli.py` and `app.py` are replaceable interfaces over the same services.

Dependency edges point from a precedent to its dependent formula cell. Cell
identifiers use `Sheet!A1`; workbook-level metadata records named ranges,
visibility, merged ranges, and external links separately.

## Determinism

The analyzer does not calculate formulas and does not call external APIs.
Rules operate on formula text, workbook structure, and dependency topology.
Time is supplied through an injectable clock. Synthetic samples use a fixed
seed and fixed workbook metadata.

## Non-destructive output

The input file is opened for reading, hashed before and after analysis, and
never saved. The annotated `.xlsx` exporter loads a fresh copy and saves only
to a distinct output path.
