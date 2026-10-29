-- SQL equivalents of the 25 Python checks in src/checks.py.
-- Run against a SQLite database loaded from data/*.csv (see run_all.py,
-- which executes this file and compares every count with the Python run).
-- Reference date for freshness checks: 2026-10-15.

SELECT 'DQ01' AS check_id, COUNT(*) AS violations FROM loans WHERE loan_id IS NULL
UNION ALL SELECT 'DQ02', COUNT(*) FROM loans WHERE credit_score IS NULL
UNION ALL SELECT 'DQ03', COUNT(*) FROM loans WHERE interest_rate IS NULL
UNION ALL SELECT 'DQ04', COUNT(*) FROM loans WHERE credit_score IS NOT NULL AND (credit_score < 300 OR credit_score > 850)
UNION ALL SELECT 'DQ05', COUNT(*) FROM loans WHERE interest_rate IS NOT NULL AND (interest_rate <= 0 OR interest_rate > 30)
UNION ALL SELECT 'DQ06', COUNT(*) FROM loans WHERE term_months NOT IN (12, 24, 36, 48, 60, 72, 84)
UNION ALL SELECT 'DQ07', COUNT(*) FROM loans WHERE loan_status NOT IN ('Current', 'Delinquent', 'Default', 'Paid Off', 'Charged Off')
UNION ALL SELECT 'DQ08', COALESCE(SUM(cnt - 1), 0) FROM (SELECT COUNT(*) AS cnt FROM loans GROUP BY loan_id HAVING COUNT(*) > 1)
UNION ALL SELECT 'DQ09', COALESCE(SUM(cnt - 1), 0) FROM (SELECT COUNT(*) AS cnt FROM vehicles GROUP BY vin HAVING COUNT(*) > 1)
UNION ALL SELECT 'DQ10', COUNT(*) FROM loans WHERE borrower_id NOT IN (SELECT borrower_id FROM borrowers)
UNION ALL SELECT 'DQ11', COUNT(*) FROM loans WHERE vehicle_id NOT IN (SELECT vehicle_id FROM vehicles)
UNION ALL SELECT 'DQ12', COUNT(*) FROM loans WHERE dealer_id NOT IN (SELECT dealer_id FROM dealers)
UNION ALL SELECT 'DQ13', COUNT(*) FROM payments WHERE loan_id NOT IN (SELECT loan_id FROM loans)
UNION ALL SELECT 'DQ14', COUNT(*) FROM loans WHERE julianday('2026-10-15') - julianday(last_payment_date) > 45
UNION ALL SELECT 'DQ15', COUNT(*) FROM loans WHERE julianday('2026-10-15') - julianday(updated_at) > 60
UNION ALL SELECT 'DQ16', COUNT(*) FROM loans WHERE current_balance < 0 OR current_balance > loan_amount
UNION ALL SELECT 'DQ17', COUNT(*) FROM loans WHERE loan_amount > 0 AND (down_payment < 0 OR down_payment >= loan_amount)
UNION ALL SELECT 'DQ18', COUNT(*) FROM loans WHERE interest_rate IS NOT NULL AND date(origination_date, '+' || term_months || ' months') <> maturity_date
UNION ALL SELECT 'DQ19', COUNT(*) FROM loans WHERE (delinquency_days > 0) <> (loan_status IN ('Delinquent', 'Default', 'Charged Off'))
UNION ALL SELECT 'DQ20', COUNT(*) FROM loans WHERE interest_rate IS NOT NULL AND (
    CASE
      WHEN interest_rate = 0 THEN ABS(monthly_payment - loan_amount * 1.0 / term_months) / (loan_amount * 1.0 / term_months) > 0.01
      ELSE ABS(monthly_payment - loan_amount * (interest_rate / 1200.0) * pow(1 + interest_rate / 1200.0, term_months) / (pow(1 + interest_rate / 1200.0, term_months) - 1))
           / (loan_amount * (interest_rate / 1200.0) * pow(1 + interest_rate / 1200.0, term_months) / (pow(1 + interest_rate / 1200.0, term_months) - 1)) > 0.01
    END)
UNION ALL SELECT 'DQ21', COUNT(*) FROM loans WHERE vehicle_year < 1990 OR vehicle_year > 2026
UNION ALL SELECT 'DQ22', COUNT(*) FROM loans WHERE annual_income <= 0
UNION ALL SELECT 'DQ23', COUNT(*) FROM payments WHERE amount_paid < 0 OR payment_status NOT IN ('Completed', 'Pending', 'Failed', 'Reversed')
UNION ALL SELECT 'DQ24', COUNT(*) FROM loans WHERE next_payment_due_date < last_payment_date
UNION ALL SELECT 'DQ25', COUNT(*) FROM loans WHERE loan_amount <= 0 OR ltv_ratio <= 0 OR ltv_ratio > 1.2;
