# Security Policy

## Supported versions

Security fixes are provided for the latest `0.1.x` release line.

| Version | Supported |
|---|---|
| 0.1.x | Yes |
| Earlier development snapshots | No |

## Reporting a vulnerability

Use GitHub private vulnerability reporting for this repository. Do not open a
public issue for a suspected vulnerability.

Include:

- affected version and operating system;
- minimal reproduction steps;
- expected and observed security boundary;
- a synthetic workbook if one is essential;
- whether data exposure, source modification, code execution, or denial of
  service is involved.

Do not include production workbooks, credentials, tokens, personal data,
customer records, or internal hostnames.

An acknowledgement is targeted within seven days. Remediation timing depends on
severity and reproducibility; coordinated disclosure details will be agreed in
the private report.

## Data boundary

SheetPilot Beacon analyzes files locally. The core performs no network
requests. HTML and JSON reports omit raw constant values and redact common
credential patterns in formula and external-link evidence.

The annotated `.xlsx` is a full source copy with audit material added; it
retains the original workbook data and must be protected accordingly.

See [Privacy and Security](docs/PRIVACY_AND_SECURITY.md) for the complete threat
model, controls, and residual risks.
