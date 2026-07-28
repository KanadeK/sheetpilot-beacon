# Synthetic sample workbooks

These three `.xlsx` files are generated entirely by
`sheetpilot_beacon.adapters.samples` and are licensed under this repository's
MIT License. They contain no customer, production, or scraped data.

| Workbook | Scenario | Seeded findings |
|---|---|---:|
| `budget_model.xlsx` | Department budget with hidden assumptions | 5 |
| `sales_forecast.xlsx` | Regional forecast with a legacy external rate | 5 |
| `engineering_boq.xlsx` | Bill of quantities and cost roll-up | 5 |

`expected_findings.json` is the executable contract. Integration tests compare
every detected `(code, sheet, cell)` tuple with that manifest and fail on both
missing findings and unexpected extras.

Regenerate the files with:

```bash
python scripts/generate_samples.py
```
