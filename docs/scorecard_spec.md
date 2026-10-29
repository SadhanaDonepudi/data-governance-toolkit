# Power BI data quality scorecard — spec

The scorecard is a Power BI report fed by `outputs/scorecard.csv`, which
`run_all.py` regenerates on every run. One row per check (DQ01–DQ25).

## Source

- File: `outputs/scorecard.csv` (committed; regenerate with `python run_all.py`)
- Grain: one row per check per run.
- Columns: `check_id, dimension, table, field, rows_checked, violations,
  violation_rate, status, severity, data_owner, owner_email`.

## Measures (DAX)

```dax
DQ Score = DIVIDE ( COUNTROWS ( FILTER ( Scorecard, Scorecard[status] = "PASS" ) ),
                    COUNTROWS ( Scorecard ) ) * 100

Total Violations = SUM ( Scorecard[violations] )

Failed Checks = COUNTROWS ( FILTER ( Scorecard, Scorecard[status] = "FAIL" ) )

Critical Failures = COUNTROWS ( FILTER ( Scorecard,
    Scorecard[status] = "FAIL" && Scorecard[severity] = "Critical" ) )
```

## Pages / visuals

1. **Overview KPI cards:** DQ Score, Failed Checks, Critical Failures,
   Total Violations.
2. **Checks table:** all 25 checks with conditional formatting on
   `status` (green PASS / red FAIL) and `severity`.
3. **Violations by dimension:** bar chart of `violations` grouped by
   `dimension` (Completeness, Validity, Duplicates, Freshness, and the
   extended dimensions: Consistency, Range, Referential integrity,
   Uniqueness, Timeliness).
4. **Violations by owner:** bar chart grouped by `data_owner`, used by
   the alert workflow to route failures.

## Refresh

The scorecard is a static export in this repo: re-run `run_all.py` and
refresh the Power BI dataset. In production the same CSV shape would be
written by the scheduled pipeline and the report would refresh on that
schedule; the alert flow (`power-automate-flow.json`) reads the same file.

## Reading the headline score honestly

The synthetic portfolio deliberately injects one defect class per check,
so the score on this dataset is low by design (see the README's
"Resume claims vs measured results" section). On a defect-free portfolio
every check passes and the score is 100 — verified by the test suite
(`tests/test_governance.py::test_all_checks_pass_on_clean_data`).
