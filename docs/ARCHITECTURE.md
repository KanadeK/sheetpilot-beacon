# Architecture

SheetPilot Beacon is a local, deterministic static-analysis pipeline. Workbook
I/O and presentation are replaceable adapters around a typed domain core.

## Dependency direction

```text
interfaces
  cli.py ─────┐
  app.py ─────┼──> services
  Python API ─┘      audit.py · diff.py · demo.py
                          │
                          v
                       domain
  models.py · formulas.py · graph.py · detectors.py · drift.py · redaction.py
                          ^
                          │
                       adapters
          xlsx.py · exporters.py · samples.py
```

The domain does not import Streamlit, openpyxl, or network clients. Services
coordinate domain operations and enforce source integrity. Interfaces translate
user actions into service calls.

## Audit data flow

1. `audit_workbook` hashes the source bytes.
2. `read_workbook` validates `.xlsx`, size, and worksheet extent, then opens it
   with `data_only=False` and `keep_links=True`.
3. Formulas and structural metadata become an immutable `WorkbookSnapshot`.
   Constant cells retain only type and SHA-256 fingerprint.
4. Formula references are parsed and expanded within a bounded cell limit.
5. NetworkX graphs are built with edges from precedent to dependent.
6. Detectors create immutable `AuditIssue` records.
7. The source is hashed again. A mismatch raises
   `SourceWorkbookChangedError`; no report is returned.
8. Exporters create HTML, JSON, or a separately saved annotated workbook.

The source workbook is never passed to `Workbook.save`.

## Graph model

Cell identifiers use `Sheet!A1`. A dependency edge `Inputs!B2 → Model!C7`
means `Model!C7` references `Inputs!B2`. Named ranges are resolved to their
destinations when available. Workbook-level external references are retained as
redacted metadata and graph tokens.

Sheet dependencies are a projection of cell edges. Cycles are detected on the
cell graph. Fanout uses out-degree because edges point from precedent to
dependent.

## Detector policy

`DetectorConfig` makes heuristics explicit:

- fanout threshold: `8`
- minimum formulas for a copy-pattern decision: `3`
- dominant-pattern consensus: `0.75`
- maximum expanded cells per referenced range: `10,000`

Every issue is deduplicated by `(code, sheet, cell)`. Findings contain
machine-readable code and severity plus human evidence and a recommendation.
The synthetic sample manifest tests both missed findings and unexpected extras.

## Formula drift

Two snapshots are compared by sheet and coordinate. Formula text is normalized
for formula comparisons. Constants use their type-aware fingerprints, allowing
change detection without retaining the original value. `DriftKind` distinguishes
formula, constant, and sheet transitions.

## Export boundaries

- HTML and JSON contain hashes, workbook structure, metrics, redacted formula
  evidence, and findings. They omit raw constant values.
- Annotated output starts from a fresh load of the source and saves to a
  different path. It necessarily retains original workbook data.
- Workbook-controlled strings are HTML-escaped.
- Text beginning with `=`, `+`, `-`, or `@` is prefixed before being written
  into generated audit cells.

## Determinism and reproducibility

The analyzer does not calculate formulas or call external APIs. Audit time is
provided by a `Clock` protocol. Tests use `FixedClock`; interactive runs use an
aware UTC clock. Samples are generated from code with fixed workbook metadata
and have a checked-in exact-finding manifest.

## Resource boundaries

The reader defaults to a 100 MiB file limit and a 1,000,000-cell worksheet
extent. Formula ranges expand to at most 10,000 cells. These are denial-of-
service controls, not promises that every workbook below each limit will fit
every machine.

## Extension points

- Add detectors as pure functions over `WorkbookSnapshot`.
- Add report formats as adapters over `AuditReport` or `DriftReport`.
- Add interfaces over services without importing them into the domain.
- Preserve typed models and the source-integrity check when adding new readers.
