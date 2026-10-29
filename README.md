# Data Governance Toolkit — Data Quality, Metadata & Lineage

A self-contained data governance toolkit for a synthetic auto-loan
portfolio: 25 runnable data quality checks (Python **and** SQL),
a 62-field metadata catalog, metric lineage documentation, a Power
Automate owner-alert flow spec with a working simulated implementation,
and a simulated response-time experiment.

**All data in this repo is synthetic.** Nothing here comes from a real
loan book, borrower, or dealer. Names, VINs, and contact details are
generated placeholders.

## What it does

1. **Generates the portfolio** — `src/generate_data.py` builds a
   deterministic synthetic auto-loan portfolio (seed 42): 5,010 loan
   rows (5,000 base + 10 deliberate duplicate rows), 4,200 borrowers,
   4,800 vehicles, 120 dealers, 14,959 payments. One defect class is
   deliberately injected per check so every check has something real to
   catch; defect counts are recorded in
   `outputs/generation_report.json`.
2. **Runs 25 data quality checks** — `src/checks.py` (Python) and
   `sql/checks.sql` (SQLite) implement the same 25 checks across 10
   dimensions: completeness, validity, duplicates, freshness,
   consistency, range, referential integrity, uniqueness, timeliness,
   and one combined range check. Every check produces a pass/fail plus
   a measured violation count and rate.
3. **Writes a scorecard** — `outputs/scorecard.csv`, one row per check,
   is the feed for the Power BI scorecard specified in
   `docs/scorecard_spec.md`.
4. **Alerts data owners** — `src/alerting.py` implements the Power
   Automate flow specified in `docs/power-automate-flow.json`: one
   alert per failed check, addressed to that check's data owner.
   Dispatch is **simulated** (logged to `outputs/alert_log.csv`, no
   email is sent).
5. **Simulates response time** — `src/alerting.py` compares the old
   manual-review pattern against the automated-alert pattern on the
   same 500-issue synthetic stream (see "Response-time experiment").

## How to run

```bash
pip install -r requirements.txt
python run_all.py        # generate data → 25 checks → scorecard → alerts → simulation
python -m pytest tests/  # 12 tests
```

Generated data lands in `data/` (git-ignored; regenerate locally).
Small outputs — scorecard, SQL comparison, alert log, run summary —
are committed under `outputs/`.

## Measured results (this run, seed 42)

25 checks, 24 FAIL / 1 PASS, **DQ score 4.0%**, 614 total violations,
24 simulated owner alerts. All 25 SQL check counts match the Python
counts exactly (`outputs/sql_check_results.csv`).

| Check | Dimension | Table.Field | Violations | Rate | Severity |
|-------|-----------|-------------|-----------:|-----:|----------|
| DQ01 | Completeness | loans.loan_id | 0 | 0.00% | — |
| DQ02 | Completeness | loans.credit_score | 25 | 0.50% | Medium |
| DQ03 | Completeness | loans.interest_rate | 15 | 0.30% | Medium |
| DQ04 | Validity | loans.credit_score | 18 | 0.36% | Medium |
| DQ05 | Validity | loans.interest_rate | 12 | 0.24% | Medium |
| DQ06 | Validity | loans.term_months | 10 | 0.20% | Medium |
| DQ07 | Validity | loans.loan_status | 8 | 0.16% | Medium |
| DQ08 | Uniqueness | loans.loan_id | 10 | 0.20% | Medium |
| DQ09 | Uniqueness | vehicles.vin | 12 | 0.25% | Medium |
| DQ10 | Referential integrity | loans.borrower_id | 20 | 0.40% | Medium |
| DQ11 | Referential integrity | loans.vehicle_id | 15 | 0.30% | Medium |
| DQ12 | Referential integrity | loans.dealer_id | 10 | 0.20% | Medium |
| DQ13 | Referential integrity | payments.loan_id | 25 | 0.17% | Medium |
| DQ14 | Freshness | loans.last_payment_date | 120 | 2.40% | Critical |
| DQ15 | Freshness | loans.updated_at | 80 | 1.60% | High |
| DQ16 | Range | loans.current_balance | 22 | 0.44% | Medium |
| DQ17 | Range | loans.down_payment | 14 | 0.28% | Medium |
| DQ18 | Consistency | loans.maturity_date | 30 | 0.60% | High |
| DQ19 | Consistency | loans.delinquency_days/loan_status | 40 | 0.80% | High |
| DQ20 | Consistency | loans.monthly_payment | 25 | 0.50% | High |
| DQ21 | Range | loans.vehicle_year | 9 | 0.18% | Medium |
| DQ22 | Range | loans.annual_income | 11 | 0.22% | Medium |
| DQ23 | Validity | payments.amount_paid/payment_status | 32 | 0.21% | Medium |
| DQ24 | Timeliness | loans.next_payment_due_date | 28 | 0.56% | High |
| DQ25 | Range | loans.loan_amount/ltv_ratio | 23 | 0.46% | Medium |

The DQ score is low **by design**: the synthetic portfolio injects a
defect class for nearly every check so the checks have something to
catch. On a defect-free portfolio all 25 checks pass (score 100),
verified by `test_all_checks_pass_on_clean_data`.

## Response-time experiment (simulation, not production)

500 synthetic issues, same stream under both patterns. "Response time"
= time from issue occurrence to owner acknowledgement + triage (not
full remediation).

| Pattern | Mean | Median | Same-day (≤24h) |
|---------|-----:|-------:|------:|
| Manual review (3-day review cycle + 8–24h triage) | 50.26 h (2.09 days) | 49.24 h | 14.0% |
| Automated alerts (immediate alert + 1–4h triage) | 4.40 h (0.18 days) | 3.95 h | 100.0% |

Improvement: **11.4× faster on mean response time** in simulation.

## Resume claims vs measured results

Honest comparison against the resume bullets this project was built from:

| Resume claim | Measured result | Verdict |
|---|---|---|
| 25 automated data quality checks in Python and SQL (completeness, validity, duplicates, freshness) | Exactly 25 checks, each implemented in Python **and** SQL with identical counts; the four claimed dimensions are covered plus consistency, range, referential integrity, uniqueness, and timeliness | ✅ Matches |
| Results logged to a Power BI data quality scorecard | Scorecard CSV written (`outputs/scorecard.csv`) with a full Power BI spec (`docs/scorecard_spec.md`); the report itself is a spec, not a published .pbix | ⚠️ Partial — spec + feed, no live Power BI file |
| Data dictionary / metadata catalog for 60+ fields | 62 fields catalogued across 5 tables (`docs/data_dictionary.csv`), each with type, definition, source, allowed values, owner, sensitivity | ✅ Matches (62 ≥ 60) |
| Lineage tracing each dashboard metric from source file to report | 8 dashboard metrics traced source → transformation → report (`docs/lineage.md`) | ✅ Matches |
| Automated Power Automate workflow emailing data owners on failure | Flow spec written (`docs/power-automate-flow.json`) + working Python implementation (`src/alerting.py`) that produced 24 alerts on this run | ⚠️ Partial — spec + simulated dispatch, not a live flow; **no email was actually sent** |
| Cut issue response time from 3 days to same day in testing | Simulated: manual mean 2.09 days → automated mean 4.40 h (same day); same-day rate 14.0% → 100.0% | ⚠️ Partial — direction and "same day" outcome match, but the measured manual **mean is 2.09 days, not 3 days** (3 days is the review-cycle length / worst-case wait, not the mean); and this is a **simulation, not a production measurement** |

## Project structure

```
data-governance-toolkit/
├── run_all.py               # end-to-end run: data → checks → scorecard → alerts → simulation
├── src/
│   ├── generate_data.py     # deterministic synthetic portfolio + injected defects
│   ├── checks.py            # the 25 Python checks
│   └── alerting.py          # owner alerts (simulated dispatch) + response-time simulation
├── sql/
│   └── checks.sql           # the same 25 checks as SQL (verified identical counts)
├── tests/
│   └── test_governance.py   # 12 tests, all passing
├── docs/
│   ├── data_dictionary.csv  # 62-field metadata catalog
│   ├── lineage.md           # 8 dashboard metrics traced source → report
│   ├── scorecard_spec.md    # Power BI scorecard spec (measures, visuals)
│   └── power-automate-flow.json  # alert flow spec (not a live flow)
├── outputs/                 # scorecard, SQL comparison, alert log, run summary (small files)
└── data/                    # generated CSVs (git-ignored; regenerate with run_all.py)
```

## Caveats

- **All data is synthetic.** Borrower names, VINs, emails, and ZIPs are
  generated placeholders; treat sensitivity labels as documentation of
  what the real fields would require, not as handling of real PII.
- **Email dispatch is simulated.** `src/alerting.py` logs alerts to
  `outputs/alert_log.csv` and prints `[SIMULATED EMAIL]` lines. The
  Power Automate flow is a JSON spec, not a deployed flow.
- **Response-time figures are simulated**, not measured in production.
  "3 days to same day" is not reproduced exactly: the simulated manual
  mean is 2.09 days (the 3-day figure matches the review-cycle length).
- **No live Power BI report** is included; the repo ships the scorecard
  feed and the report spec.
- Results are reproducible: fixed seeds (data 42, simulation 7) mean
  `python run_all.py` reproduces every number in this README.
