# Changelog

All notable changes are documented here. This project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

No changes yet.

## [0.1.0] - 2026-07-28

### Added

- Offline `.xlsx` ingestion for formulas, named ranges, hidden sheets, merged
  ranges, and external links.
- Cell and sheet dependency graphs backed by NetworkX.
- Seven evidence-based risk detectors with configurable fanout and range
  expansion thresholds.
- Formula and sheet drift comparison, including formula-to-constant
  replacement and privacy-preserving constant fingerprints.
- HTML, JSON, and annotated-workbook exporters that never save the source.
- CLI scan, diff, demo, and local Streamlit web workflows.
- Three MIT-licensed synthetic workbooks with an exact 15-finding contract.
- Unit, integration, privacy, regression, Streamlit, and subprocess E2E
  coverage.
- Reproducible benchmark, static demo, and live-interface screenshot tooling.

### Security

- Redaction of credential-shaped formula and external-link evidence.
- HTML escaping and Excel formula-injection protection in generated audit
  fields.
- Explicit file, worksheet-extent, and formula-range limits.
- Source SHA-256 checks before and after every audit.

### Fixed

- Scoped Polars CPU-check override for Windows sandboxes that do not expose the
  host architecture, with environment restoration.
- Project-local pytest temporary directories in the unified verifier, avoiding
  false failures from an inaccessible global temporary directory.

[Unreleased]: https://github.com/KanadeK/sheetpilot-beacon/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/KanadeK/sheetpilot-beacon/releases/tag/v0.1.0
