# Privacy and Security

## Security objective

SheetPilot Beacon should let a user inspect workbook structure and formula risk
without transferring the workbook, modifying the source, or serializing raw
constant values into machine-readable reports.

It is a static audit aid, not a sandbox, malware scanner, DLP product, or
financial-model certification system.

## Threat model

An `.xlsx` file is an untrusted ZIP-based package. It can be corrupt, very
large, intentionally sparse, contain confidential values, embed credentials in
formula URLs, reference internal paths, or contain text designed to inject HTML
or spreadsheet formulas into generated output.

The local machine and Python environment are assumed to be controlled by the
user. A compromised dependency or operating system is outside this threat
model.

## Data-flow boundary

```text
source.xlsx
    │ local read
    v
structure + formulas + value fingerprints
    │
    ├── HTML / JSON: no raw constant values
    └── annotated.xlsx: full source copy + generated audit sheet
```

The CLI, domain core, and local Streamlit app contain no HTTP client and no
telemetry. The GitHub Pages demo is pre-generated from synthetic samples and
does not accept files.

## Implemented controls

### Input handling

- Accept `.xlsx` only.
- Default maximum file size: 100 MiB.
- Default maximum worksheet extent: 1,000,000 cells.
- Default expanded formula-range limit: 10,000 cells.
- Open with formula text retained; never execute macros or calculate formulas.
- Convert parser failures into explicit errors.

### Data minimization

- Constant values become type-aware SHA-256 fingerprints.
- HTML and JSON reports do not contain raw constant values.
- Formula and external-link text is limited and passed through credential-
  pattern redaction.
- Audit timestamps are aware UTC values; no user identity is collected.

### Output safety

- Workbook-controlled strings are escaped before entering HTML.
- Generated workbook fields that begin with `=`, `+`, `-`, or `@` are prefixed
  as text.
- The source and annotated output paths must differ.
- The source hash is checked before and after analysis.
- A generated audit-sheet name avoids collisions with existing workbook
  sheets.

### Supply chain

- Python is fixed to the 3.12 line.
- `uv.lock` records resolved direct and transitive dependencies.
- CI performs lint, strict type checks, full tests, isolated builds, dependency
  audit, secret scan, and release checksum generation.
- GitHub workflow permissions are minimized per job.

## Redaction scope

Redaction covers common assignment shapes such as `api_key=...`,
`access_token: ...`, `password=...`, and recognizable GitHub, OpenAI, and Slack
token prefixes. It preserves surrounding formula structure so a finding remains
actionable.

Redaction is best effort. A novel or encoded secret may not match. Formula text,
sheet names, file names, external book names, and business structure may still
be sensitive even when values are absent.

## Annotated-workbook warning

The annotated `.xlsx` is deliberately a full copy of the source with findings
added. It therefore retains all original values, formulas, metadata, and
embedded content supported by openpyxl. Treat it with the same sensitivity as
the source. The privacy-minimized artifacts are the HTML and JSON reports.

## Residual risks and unsupported content

- No guarantee is made for `.xls`, `.xlsb`, `.xlsm`, encrypted workbooks, VBA,
  Power Query, data connections, embedded OLE objects, or every Excel extension
  formula.
- An already-corrupt workbook may still trigger an Excel repair prompt in an
  annotated copy.
- Static dependency analysis can have false positives and false negatives.
- Formula evaluation and calculated-value correctness are outside scope.
- Very complex packages below configured size limits can still consume
  significant memory or CPU.

## Safe operating guidance

1. Work on a copy when handling irreplaceable input.
2. Run the tool on a trusted local machine.
3. Review every report before sharing it.
4. Keep annotated copies inside the source workbook's trust boundary.
5. Use only synthetic workbooks in public issues and pull requests.
6. Verify Release artifacts against `SHA256SUMS.txt`.

## Vulnerability reporting

Use GitHub private vulnerability reporting for this repository. Do not attach a
production workbook, token, customer record, or personal data. A minimal
synthetic workbook that demonstrates the issue is preferred. See
[SECURITY.md](../SECURITY.md).
