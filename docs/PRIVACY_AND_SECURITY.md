# Privacy and Security

## Threat model

Workbooks can contain confidential values, formulas with embedded URLs, hidden
sheets, and links to internal files. They are also ZIP containers and may be
malformed or unexpectedly large.

## Controls

- Analysis is offline and has no telemetry.
- Only `.xlsx` Open XML workbooks are accepted by the MVP.
- Reports exclude raw cell values.
- Formula and external-link evidence is redacted for credential-shaped text
  and sensitive URL query parameters.
- Output paths must differ from the source path.
- A bounded cell/range expansion limit prevents a formula from creating an
  unbounded dependency graph.
- Parser failures are explicit errors rather than successful empty reports.
- The source SHA-256 is checked before and after every audit.

## Residual risks

- Formulas can reveal sheet names and business structure even without values.
- Excel may display a repair prompt for already-corrupt input packages.
- Macros and legacy `.xls` files are outside the `v0.1.0` scope.
- Formula evaluation is delegated to Excel; this project performs static
  analysis and does not assert calculated-value correctness.

Review generated reports before sharing them outside the workbook's original
trust boundary.
