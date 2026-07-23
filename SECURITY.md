# Security Policy

## Supported version

Security fixes are provided for the latest `0.1.x` release line.

## Reporting a vulnerability

Use GitHub's private vulnerability-reporting form for this repository. Do not
include production workbooks, credentials, tokens, personal data, or customer
records. A minimal synthetic workbook is preferred.

## Data boundary

SheetPilot Beacon analyzes files locally. The core analyzer performs no network
requests. Reports omit cell values by default and redact common secret patterns
that could appear inside formulas or external-link text. Annotated output is a
new copy; the source workbook is never saved by the application.
