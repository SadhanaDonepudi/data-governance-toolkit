# Lineage: source file → transformation → dashboard metric

Every metric below is traced from its source file and fields, through the
transformation applied, to the report metric. "Guarded by" lists the data
quality checks that must pass for the metric to be trusted.

## 1. Portfolio Balance

- **Source:** `loans.csv` — `current_balance`
- **Transformation:** `SUM(current_balance)` over all loans, excluding rows
  flagged by DQ16 (balance outside `[0, loan_amount]`).
- **Report metric:** Total outstanding balance, USD.
- **Guarded by:** DQ01, DQ16, DQ08 (unique loan rows, no double counting).

## 2. Active Loan Count

- **Source:** `loans.csv` — `loan_id`, `loan_status`
- **Transformation:** `COUNT(DISTINCT loan_id)` where `loan_status` is not
  `Paid Off`; duplicate loan rows are removed first.
- **Report metric:** Number of active loans.
- **Guarded by:** DQ01, DQ07, DQ08.

## 3. Delinquency Rate

- **Source:** `loans.csv` — `delinquency_days`, `loan_status`
- **Transformation:** share of active loans with `delinquency_days > 0`.
  Rows where the two fields disagree are quarantined before the ratio is
  computed.
- **Report metric:** % of active loans past due.
- **Guarded by:** DQ19, DQ07, DQ14 (stale payment dates would understate it).

## 4. Average Credit Score

- **Source:** `loans.csv` — `credit_score`
- **Transformation:** `AVG(credit_score)` over non-null values in
  `[300, 850]`; nulls and out-of-range values are excluded and counted
  separately.
- **Report metric:** Mean borrower credit score at origination.
- **Guarded by:** DQ02, DQ04.

## 5. Average Interest Rate

- **Source:** `loans.csv` — `interest_rate`
- **Transformation:** `AVG(interest_rate)` over non-null values in `(0, 30]`.
- **Report metric:** Mean annual interest rate, %.
- **Guarded by:** DQ03, DQ05, DQ20 (payment consistency depends on the rate).

## 6. Average LTV

- **Source:** `loans.csv` — `ltv_ratio`, `loan_amount`
- **Transformation:** `AVG(ltv_ratio)` over rows with `0 < ltv_ratio <= 1.2`
  and `loan_amount > 0`.
- **Report metric:** Mean loan-to-value ratio at origination.
- **Guarded by:** DQ25, DQ17.

## 7. Payment Completion Rate

- **Source:** `payments.csv` — `payment_status`, `loan_id`
- **Transformation:** share of payments with `payment_status = 'Completed'`,
  after dropping payments whose `loan_id` has no matching loan and rows
  with negative `amount_paid`.
- **Report metric:** % of posted payments completed.
- **Guarded by:** DQ13, DQ23.

## 8. Data Quality Score

- **Source:** `outputs/scorecard.csv` — one row per check (DQ01–DQ25)
- **Transformation:** `100 * (checks with status PASS) / 25`.
- **Report metric:** Headline scorecard KPI (see `scorecard_spec.md`).
- **Guarded by:** all checks DQ01–DQ25; a failing check lowers the score
  and triggers an owner alert (see `power-automate-flow.json`).
