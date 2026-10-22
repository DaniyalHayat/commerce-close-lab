# Workbook guide

Open `workbooks/model.xlsx` in desktop Microsoft Excel. The workbook has live formulas and a native PivotTable. The Python pipeline and the checked-in workbook initially use the same synthetic inputs.

## Regenerate inputs

```bash
python run.py
python refresh_workbook.py
```

Close the workbook before running the refresh script. The script updates source cells only, preserves formulas and native PivotTable objects, and requests full recalculation and PivotTable refresh on open. After refreshing, open the workbook in Excel, use **Data > Refresh All**, recalculate, and save. Until then, cached values and the PivotTable cache may be stale. Always check the reconciliations after an input change.

The template intentionally enforces the original record counts. If a different dataset changes the row counts, the script stops rather than truncating data or leaving SUMIFS/PivotTable source ranges incomplete. Extend the source ranges, formulas, charts and any native PivotTable source bounds deliberately before using a different shape. Do not treat prior `excel_verification.json` as a newly executed verification after changes.

The SQL databases are generated locally and excluded from Git. CSVs, analysis JSON, HTML, workbook, source and tests are included in the repository.

## Excel features

- `Journals!F5:F4187`: exact-match VLOOKUP maps account IDs to the Accounts sheet.
- `Trial balance`: SUMIFS calculates debit and credit turnover; MAX separates debit and credit balances.
- `Pivot review`: native PivotTable aggregates debit and credit activity by account.
- `Exceptions`: seeded findings remain Open. Changing the displayed status is not a journal correction or accounting approval.
- `Checks`: trial balance, processor clearing, customer advances and AP reconcile; bank-to-book remains intentionally nonzero.

The Summary status remains incomplete with open exceptions. There is no automatic journal approval or unsupported claim that exceptions have been resolved. Proposed reviewers in the memo are case-study responsibilities.
