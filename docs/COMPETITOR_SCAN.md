# Public Repository Competitor Scan

Scan date: 2026-07-23 (UTC+8)

Method: GitHub CLI repository search against public metadata

Authenticated account used for the scan: `KanadeK`

## Name check

The exact queries `"SheetPilot Beacon"` and `sheetpilot-beacon` returned no
public repositories. `KanadeK/sheetpilot-beacon` also did not exist at scan
time. The project therefore retains the name **SheetPilot Beacon** and slug
`sheetpilot-beacon`.

## Queries

- `"SheetPilot Beacon"`
- `sheetpilot-beacon`
- `excel formula audit`
- `spreadsheet formula analysis`
- `excel formula language:python`
- `excel dependency graph`
- `xlsx audit`
- `spreadsheet quality`
- `excel formula parser`

Stars and update timestamps are point-in-time GitHub metadata, not popularity
or quality guarantees.

## Most relevant sampled repositories

| Repository | Stars | Updated (UTC) | Main capability | Overlap and boundary |
|---|---:|---|---|---|
| [vinci1it2000/formulas](https://github.com/vinci1it2000/formulas) | 497 | 2026-07-22 | Python Excel formula interpreter | Formula parsing/evaluation; not an audit-and-drift workflow |
| [bradbase/xlcalculator](https://github.com/bradbase/xlcalculator) | 162 | 2026-06-30 | Converts and evaluates Excel formulas | Formula execution overlap; no annotated risk report contract |
| [fabiooshiro/xlsx-calc](https://github.com/fabiooshiro/xlsx-calc) | 122 | 2026-06-21 | JavaScript formula parser/calculator | Formula engine in another runtime; not structural auditing |
| [knowledgestack/excel-parser](https://github.com/knowledgestack/excel-parser) | 47 | 2026-07-22 | LLM-oriented XLSX extraction and dependency graphs | Strong parsing/graph overlap; different RAG/citation goal, no risk drift focus |
| [aidhound/hotxlfp](https://github.com/aidhound/hotxlfp) | 31 | 2026-07-23 | Python formula parser | Parser component only |
| [psalaets/excel-formula-parser](https://github.com/psalaets/excel-formula-parser) | 28 | 2026-02-06 | Formula-to-tree parser | Syntax-tree overlap; no workbook audit pipeline |
| [jiteshgurav/formula-dependency-excel](https://github.com/jiteshgurav/formula-dependency-excel) | 16 | 2026-06-01 | Cell dependency discovery | Direct graph overlap; narrower than detection, diff, and exports |
| [pressw-llc/excel-explorer](https://github.com/pressw-llc/excel-explorer) | 6 | 2026-06-15 | CLI workbook exploration and dependency tracing | Similar local inspection; no defined risk rules or annotated copy |
| [RaymondWise/Excel-Formula-Auditing-by-Aaron-Blood](https://github.com/RaymondWise/Excel-Formula-Auditing-by-Aaron-Blood) | 1 | 2025-01-15 | Re-hosted Excel formula-auditing utility | Audit goal overlap; different implementation and no reproducible Python pipeline |
| [WenYiCoding/XlsxAudit](https://github.com/WenYiCoding/XlsxAudit) | 1 | 2025-06-19 | XLSX format/change checks | Audit naming overlap; focuses on formatting/change confirmation |
| [Comuna-prog/excel-formula-auditor-showcase](https://github.com/Comuna-prog/excel-formula-auditor-showcase) | 0 | 2026-07-09 | Showcase for static formula-risk analysis | Closest detector overlap, but source is private and no reusable offline package is published |
| [Grigory-T/excel-formula-parser](https://github.com/Grigory-T/excel-formula-parser) | 0 | 2026-04-11 | Python AST printer and NetworkX graph | Parser/graph overlap; no workbook-level audit, diff, or exports |

## Differentiation decision

No sampled active repository overlaps more than roughly 70% of the MVP
contract. SheetPilot Beacon therefore keeps its original positioning and
emphasizes the combination of:

1. Static risk detection over workbook structure and dependency topology.
2. Formula-drift comparison, including formula-to-constant replacement.
3. Non-destructive HTML and annotated-copy exports with source hash evidence.
4. Three deterministic, licensed example workbooks with known findings.

This is a bounded public-repository sample, not a claim of global uniqueness.
