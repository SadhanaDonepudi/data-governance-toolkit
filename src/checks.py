"""25 data-quality checks over the synthetic auto-loan portfolio.

Each check returns one row: check_id, dimension, table, field(s), rows
checked, violation count, violation rate, and PASS/FAIL. A check FAILS when
it finds at least one violation; the scorecard reports the share of checks
passing as the headline data-quality score.

Check owners are the data owners who receive the (simulated) alert when a
check fails; see ``src/alerting.py``. Severity is derived from the
violation rate: >2% Critical, >0.5% High, >0 Medium.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

AS_OF = date(2026, 10, 15)
ALLOWED_TERMS = {12, 24, 36, 48, 60, 72, 84}
ALLOWED_STATUSES = {"Current", "Delinquent", "Default", "Paid Off", "Charged Off"}
ALLOWED_PAYMENT_STATUSES = {"Completed", "Pending", "Failed", "Reversed"}
DELINQUENT_STATUSES = {"Delinquent", "Default", "Charged Off"}
VALID_STATES = {"IL", "TX", "CA", "FL", "OH", "MI", "GA", "NC", "PA", "WI"}

# check_id -> (data owner, owner team email placeholder used by the simulator)
OWNERS = {
    "DQ01": ("Credit Risk Analytics", "credit-risk-analytics@example.com"),
    "DQ02": ("Credit Risk Analytics", "credit-risk-analytics@example.com"),
    "DQ03": ("Loan Servicing Ops", "loan-servicing-ops@example.com"),
    "DQ04": ("Credit Risk Analytics", "credit-risk-analytics@example.com"),
    "DQ05": ("Loan Servicing Ops", "loan-servicing-ops@example.com"),
    "DQ06": ("Loan Origination Ops", "loan-origination-ops@example.com"),
    "DQ07": ("Loan Servicing Ops", "loan-servicing-ops@example.com"),
    "DQ08": ("Data Engineering", "data-engineering@example.com"),
    "DQ09": ("Data Engineering", "data-engineering@example.com"),
    "DQ10": ("Data Engineering", "data-engineering@example.com"),
    "DQ11": ("Data Engineering", "data-engineering@example.com"),
    "DQ12": ("Dealer Operations", "dealer-operations@example.com"),
    "DQ13": ("Data Engineering", "data-engineering@example.com"),
    "DQ14": ("Loan Servicing Ops", "loan-servicing-ops@example.com"),
    "DQ15": ("Data Engineering", "data-engineering@example.com"),
    "DQ16": ("Loan Servicing Ops", "loan-servicing-ops@example.com"),
    "DQ17": ("Loan Origination Ops", "loan-origination-ops@example.com"),
    "DQ18": ("Loan Origination Ops", "loan-origination-ops@example.com"),
    "DQ19": ("Loan Servicing Ops", "loan-servicing-ops@example.com"),
    "DQ20": ("Loan Servicing Ops", "loan-servicing-ops@example.com"),
    "DQ21": ("Dealer Operations", "dealer-operations@example.com"),
    "DQ22": ("Credit Risk Analytics", "credit-risk-analytics@example.com"),
    "DQ23": ("Payments Ops", "payments-ops@example.com"),
    "DQ24": ("Loan Servicing Ops", "loan-servicing-ops@example.com"),
    "DQ25": ("Credit Risk Analytics", "credit-risk-analytics@example.com"),
}


def _add_months(d: date, months: int) -> date:
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    nxt = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return date(year, month, min(d.day, (nxt - timedelta(days=1)).day))


def _row(check_id, dimension, table, field, n_checked, n_viol):
    rate = n_viol / n_checked if n_checked else 0.0
    if n_viol == 0:
        severity = "None"
    elif rate > 0.02:
        severity = "Critical"
    elif rate > 0.005:
        severity = "High"
    else:
        severity = "Medium"
    owner, email = OWNERS[check_id]
    return {
        "check_id": check_id,
        "dimension": dimension,
        "table": table,
        "field": field,
        "rows_checked": int(n_checked),
        "violations": int(n_viol),
        "violation_rate": round(rate, 6),
        "status": "PASS" if n_viol == 0 else "FAIL",
        "severity": severity,
        "data_owner": owner,
        "owner_email": email,
    }


def run_checks(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    loans, borrowers = data["loans"], data["borrowers"]
    vehicles, dealers, payments = data["vehicles"], data["dealers"], data["payments"]
    out = []

    out.append(_row("DQ01", "Completeness", "loans", "loan_id",
                    len(loans), int(loans["loan_id"].isna().sum())))
    out.append(_row("DQ02", "Completeness", "loans", "credit_score",
                    len(loans), int(loans["credit_score"].isna().sum())))
    out.append(_row("DQ03", "Completeness", "loans", "interest_rate",
                    len(loans), int(loans["interest_rate"].isna().sum())))
    cs = loans["credit_score"].dropna()
    out.append(_row("DQ04", "Validity", "loans", "credit_score",
                    len(cs), int(((cs < 300) | (cs > 850)).sum())))
    ir = loans["interest_rate"].dropna()
    out.append(_row("DQ05", "Validity", "loans", "interest_rate",
                    len(ir), int(((ir <= 0) | (ir > 30)).sum())))
    out.append(_row("DQ06", "Validity", "loans", "term_months",
                    len(loans), int((~loans["term_months"].isin(ALLOWED_TERMS)).sum())))
    out.append(_row("DQ07", "Validity", "loans", "loan_status",
                    len(loans), int((~loans["loan_status"].isin(ALLOWED_STATUSES)).sum())))
    out.append(_row("DQ08", "Uniqueness", "loans", "loan_id",
                    len(loans), int(loans.duplicated(subset=["loan_id"]).sum())))
    out.append(_row("DQ09", "Uniqueness", "vehicles", "vin",
                    len(vehicles), int(vehicles.duplicated(subset=["vin"]).sum())))
    out.append(_row("DQ10", "Referential integrity", "loans", "borrower_id",
                    len(loans), int((~loans["borrower_id"].isin(set(borrowers["borrower_id"]))).sum())))
    out.append(_row("DQ11", "Referential integrity", "loans", "vehicle_id",
                    len(loans), int((~loans["vehicle_id"].isin(set(vehicles["vehicle_id"]))).sum())))
    out.append(_row("DQ12", "Referential integrity", "loans", "dealer_id",
                    len(loans), int((~loans["dealer_id"].isin(set(dealers["dealer_id"]))).sum())))
    out.append(_row("DQ13", "Referential integrity", "payments", "loan_id",
                    len(payments), int((~payments["loan_id"].isin(set(loans["loan_id"]))).sum())))
    lp = pd.to_datetime(loans["last_payment_date"])
    out.append(_row("DQ14", "Freshness", "loans", "last_payment_date",
                    len(loans), int((((pd.Timestamp(AS_OF) - lp).dt.days) > 45).sum())))
    ua = pd.to_datetime(loans["updated_at"])
    out.append(_row("DQ15", "Freshness", "loans", "updated_at",
                    len(loans), int((((pd.Timestamp(AS_OF) - ua).dt.days) > 60).sum())))
    out.append(_row("DQ16", "Range", "loans", "current_balance",
                    len(loans), int(((loans["current_balance"] < 0) | (loans["current_balance"] > loans["loan_amount"])).sum())))
    eval_dp = loans[loans["loan_amount"] > 0]  # degenerate zero-amount rows are DQ25's, not DQ17's
    out.append(_row("DQ17", "Range", "loans", "down_payment",
                    len(eval_dp), int(((eval_dp["down_payment"] < 0) | (eval_dp["down_payment"] >= eval_dp["loan_amount"])).sum())))
    # maturity consistency; rows with a null rate/term cannot be evaluated and are excluded
    eval_m = loans.dropna(subset=["interest_rate"])
    mism = 0
    for _, r in eval_m.iterrows():
        if _add_months(date.fromisoformat(r["origination_date"]), int(r["term_months"])).isoformat() != r["maturity_date"]:
            mism += 1
    out.append(_row("DQ18", "Consistency", "loans", "maturity_date", len(eval_m), mism))
    dq19 = ((loans["delinquency_days"] > 0) != loans["loan_status"].isin(DELINQUENT_STATUSES))
    out.append(_row("DQ19", "Consistency", "loans", "delinquency_days/loan_status",
                    len(loans), int(dq19.sum())))
    # amortisation consistency within 1% (rows with null rate excluded)
    mism = 0
    for _, r in eval_m.iterrows():
        amt, n, rate = float(r["loan_amount"]), int(r["term_months"]), float(r["interest_rate"])
        rr = rate / 100 / 12
        expected = amt / n if rr == 0 else amt * rr * (1 + rr) ** n / ((1 + rr) ** n - 1)
        actual = float(r["monthly_payment"])
        if expected == 0:
            bad = actual != 0
        else:
            bad = abs(actual - expected) / expected > 0.01
        mism += int(bad)
    out.append(_row("DQ20", "Consistency", "loans", "monthly_payment", len(eval_m), mism))
    out.append(_row("DQ21", "Range", "loans", "vehicle_year",
                    len(loans), int(((loans["vehicle_year"] < 1990) | (loans["vehicle_year"] > 2026)).sum())))
    out.append(_row("DQ22", "Range", "loans", "annual_income",
                    len(loans), int((loans["annual_income"] <= 0).sum())))
    dq23 = (payments["amount_paid"] < 0) | (~payments["payment_status"].isin(ALLOWED_PAYMENT_STATUSES))
    out.append(_row("DQ23", "Validity", "payments", "amount_paid/payment_status",
                    len(payments), int(dq23.sum())))
    due = pd.to_datetime(loans["next_payment_due_date"])
    out.append(_row("DQ24", "Timeliness", "loans", "next_payment_due_date",
                    len(loans), int((due < lp).sum())))
    out.append(_row("DQ25", "Range", "loans", "loan_amount/ltv_ratio",
                    len(loans), int(((loans["loan_amount"] <= 0) | (loans["ltv_ratio"] <= 0) | (loans["ltv_ratio"] > 1.2)).sum())))

    return pd.DataFrame(out)
