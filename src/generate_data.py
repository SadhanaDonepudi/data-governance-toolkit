"""Synthetic auto-loan portfolio generator.

All data is fictitious. The generator is deterministic (seed 42) so every
run reproduces the same portfolio and the same defect counts, which is what
makes the data-quality check results reproducible.

Controlled defects are injected at documented rates on disjoint row sets so
each check measures exactly one defect class. Defect counts are recorded in
``outputs/generation_report.json`` by run_all.py.
"""

from __future__ import annotations

import json
import random
import string
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

SEED = 42
N_LOANS = 5000
N_BORROWERS = 4200
N_VEHICLES = 4800
N_DEALERS = 120
AS_OF = date(2026, 10, 15)  # reference ("today") for freshness checks

MAKES_MODELS = {
    "Toyota": ["Camry", "RAV4", "Corolla"],
    "Ford": ["F-150", "Escape", "Explorer"],
    "Chevrolet": ["Silverado", "Equinox", "Malibu"],
    "Honda": ["Civic", "Accord", "CR-V"],
    "Nissan": ["Altima", "Rogue", "Sentra"],
    "Hyundai": ["Elantra", "Tucson", "Sonata"],
}
STATES = ["IL", "TX", "CA", "FL", "OH", "MI", "GA", "NC", "PA", "WI"]
TERMS = [12, 24, 36, 48, 60, 72, 84]
STATUSES = ["Current", "Delinquent", "Default", "Paid Off", "Charged Off"]
CHANNELS = ["Dealer", "Online", "Branch"]
EMPLOYMENT = ["Employed", "Self-Employed", "Retired", "Unemployed"]
PURPOSES = ["New Vehicle", "Used Vehicle", "Refinance"]


def _add_months(d: date, months: int) -> date:
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    # clamp day to end of month
    if month == 12:
        nxt = date(year + 1, 1, 1)
    else:
        nxt = date(year, month + 1, 1)
    last_day = (nxt - timedelta(days=1)).day
    return date(year, month, min(d.day, last_day))


def _vin(rng: random.Random) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(rng.choice(chars) for _ in range(17))


def generate(out_dir: Path) -> dict:
    rng = random.Random(SEED)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ---- reference tables -------------------------------------------------
    dealers = pd.DataFrame(
        {
            "dealer_id": [f"D{i:04d}" for i in range(1, N_DEALERS + 1)],
            "dealer_name": [f"Dealer {i:03d} Auto Group" for i in range(1, N_DEALERS + 1)],
            "state": [rng.choice(STATES) for _ in range(N_DEALERS)],
            "region": [rng.choice(["Midwest", "South", "West", "Northeast"]) for _ in range(N_DEALERS)],
            "dealer_tier": [rng.choice(["Tier 1", "Tier 2", "Tier 3"]) for _ in range(N_DEALERS)],
        }
    )

    borrowers = pd.DataFrame(
        {
            "borrower_id": [f"B{i:05d}" for i in range(1, N_BORROWERS + 1)],
            "first_name": [f"Borrower{i}" for i in range(1, N_BORROWERS + 1)],
            "last_name": [f"Lastname{i}" for i in range(1, N_BORROWERS + 1)],
            "date_of_birth": [
                date(rng.randint(1960, 2004), rng.randint(1, 12), rng.randint(1, 28)).isoformat()
                for _ in range(N_BORROWERS)
            ],
            "state": [rng.choice(STATES) for _ in range(N_BORROWERS)],
            "zip_code": [f"{rng.randint(10000, 99999)}" for _ in range(N_BORROWERS)],
            "credit_bureau": [rng.choice(["Equifax", "Experian", "TransUnion"]) for _ in range(N_BORROWERS)],
            "email_domain": [rng.choice(["example.com", "mail.example.org"]) for _ in range(N_BORROWERS)],
            "phone_type": [rng.choice(["Mobile", "Home", "Work"]) for _ in range(N_BORROWERS)],
            "record_created_at": [date(2024, 1, 1).isoformat()] * N_BORROWERS,
        }
    )

    vehicles = pd.DataFrame(
        {
            "vehicle_id": [f"V{i:05d}" for i in range(1, N_VEHICLES + 1)],
            "vin": [_vin(rng) for _ in range(N_VEHICLES)],
            "make": [rng.choice(list(MAKES_MODELS)) for _ in range(N_VEHICLES)],
            "model": ["" for _ in range(N_VEHICLES)],
            "model_year": [rng.randint(2015, 2026) for _ in range(N_VEHICLES)],
            "mileage": [rng.randint(0, 120000) for _ in range(N_VEHICLES)],
            "msrp": [round(rng.uniform(15000, 65000), 2) for _ in range(N_VEHICLES)],
            "vehicle_type": [rng.choice(["Sedan", "SUV", "Truck", "Hatchback"]) for _ in range(N_VEHICLES)],
            "fuel_type": [rng.choice(["Gasoline", "Hybrid", "Electric"]) for _ in range(N_VEHICLES)],
        }
    )
    vehicles["model"] = [
        rng.choice(MAKES_MODELS[m]) for m in vehicles["make"]
    ]

    # ---- loans (clean base) ----------------------------------------------
    borrower_ids = borrowers["borrower_id"].tolist()
    vehicle_ids = vehicles["vehicle_id"].tolist()
    dealer_ids = dealers["dealer_id"].tolist()
    rows = []
    for i in range(1, N_LOANS + 1):
        orig = date(rng.randint(2021, 2025), rng.randint(1, 12), rng.randint(1, 28))
        term = rng.choice(TERMS)
        amount = round(rng.uniform(8000, 60000), 2)
        down = round(amount * rng.uniform(0.05, 0.35), 2)
        rate = round(rng.uniform(3.5, 14.5), 3)
        n = term
        r = rate / 100 / 12
        pmt = round(amount * r * (1 + r) ** n / ((1 + r) ** n - 1), 2)
        status = rng.choices(
            STATUSES, weights=[0.78, 0.10, 0.04, 0.06, 0.02]
        )[0]
        delinq = 0
        if status == "Delinquent":
            delinq = rng.randint(1, 89)
        elif status in ("Default", "Charged Off"):
            delinq = rng.randint(90, 240)
        last_pay = AS_OF - timedelta(days=rng.randint(0, 30))
        if status == "Paid Off":
            bal = 0.0
        else:
            bal = round(amount * rng.uniform(0.15, 0.95), 2)
        vehicle_value = round(amount / rng.uniform(0.6, 0.95), 2)
        rows.append(
            {
                "loan_id": f"L{i:05d}",
                "borrower_id": rng.choice(borrower_ids),
                "vehicle_id": rng.choice(vehicle_ids),
                "dealer_id": rng.choice(dealer_ids),
                "origination_date": orig.isoformat(),
                "maturity_date": _add_months(orig, term).isoformat(),
                "term_months": term,
                "loan_amount": amount,
                "down_payment": down,
                "interest_rate": rate,
                "monthly_payment": pmt,
                "current_balance": bal,
                "vehicle_year": rng.randint(2015, 2026),
                "vehicle_make": rng.choice(list(MAKES_MODELS)),
                "vehicle_model": "",
                "credit_score": rng.randint(550, 820),
                "employment_status": rng.choice(EMPLOYMENT),
                "annual_income": round(rng.uniform(30000, 180000), 2),
                "state": rng.choice(STATES),
                "loan_status": status,
                "delinquency_days": delinq,
                "last_payment_date": last_pay.isoformat(),
                "next_payment_due_date": (last_pay + timedelta(days=30)).isoformat(),
                "origination_channel": rng.choice(CHANNELS),
                "co_signer_flag": rng.choice([0, 1]),
                "loan_purpose": rng.choice(PURPOSES),
                "ltv_ratio": round(amount / vehicle_value, 4),
                "dti_ratio": round(pmt * 12 / rng.uniform(30000, 180000), 4),
                "created_at": orig.isoformat(),
                "updated_at": (AS_OF - timedelta(days=rng.randint(0, 20))).isoformat(),
            }
        )
    loans = pd.DataFrame(rows)
    loans["vehicle_model"] = [
        rng.choice(MAKES_MODELS[m]) for m in loans["vehicle_make"]
    ]

    # ---- payments (clean base) --------------------------------------------
    pay_rows = []
    pid = 1
    for _, ln in loans.iterrows():
        for k in range(rng.randint(0, 6)):
            due = round(float(ln["monthly_payment"]), 2)
            pay_rows.append(
                {
                    "payment_id": f"P{pid:06d}",
                    "loan_id": ln["loan_id"],
                    "payment_date": (AS_OF - timedelta(days=rng.randint(0, 300))).isoformat(),
                    "amount_due": due,
                    "amount_paid": due if rng.random() > 0.15 else round(due * rng.uniform(0.5, 1.0), 2),
                    "payment_status": rng.choice(["Completed", "Pending", "Failed", "Reversed"]),
                    "payment_method": rng.choice(["ACH", "Card", "Check", "Cash"]),
                    "posted_at": AS_OF.isoformat(),
                }
            )
            pid += 1
    payments = pd.DataFrame(pay_rows)

    # ---- controlled defects on disjoint row sets --------------------------
    defect_counts: dict[str, int] = {}
    idx = list(loans.index)
    rng.shuffle(idx)
    cursor = 0

    def take(n: int):
        nonlocal cursor
        out = idx[cursor : cursor + n]
        cursor += n
        return out

    def record(name: str, n: int):
        defect_counts[name] = n

    sel = take(25); loans.loc[sel, "credit_score"] = None; record("credit_score_null", len(sel))
    sel = take(15); loans.loc[sel, "interest_rate"] = None; record("interest_rate_null", len(sel))
    sel = take(18); loans.loc[sel, "credit_score"] = [rng.choice([250, 900]) for _ in sel]; record("credit_score_out_of_range", len(sel))
    sel = take(12)
    loans.loc[sel, "interest_rate"] = [rng.choice([0.0, 35.0]) for _ in sel]
    # keep the amortisation check clean: recompute the payment from the new rate
    for j in sel:
        amt, n, rate = float(loans.loc[j, "loan_amount"]), int(loans.loc[j, "term_months"]), float(loans.loc[j, "interest_rate"])
        r = rate / 100 / 12
        loans.loc[j, "monthly_payment"] = round(amt / n, 2) if r == 0 else round(amt * r * (1 + r) ** n / ((1 + r) ** n - 1), 2)
    record("interest_rate_invalid", len(sel))
    sel = take(10)
    loans.loc[sel, "term_months"] = 30
    # keep the maturity check clean: move maturity to match the new term
    loans.loc[sel, "maturity_date"] = [_add_months(date.fromisoformat(d), 30).isoformat() for d in loans.loc[sel, "origination_date"]]
    # keep the amortisation check clean: recompute the payment for the new term
    for j in sel:
        amt, n = float(loans.loc[j, "loan_amount"]), 30
        r = float(loans.loc[j, "interest_rate"]) / 100 / 12
        loans.loc[j, "monthly_payment"] = round(amt * r * (1 + r) ** n / ((1 + r) ** n - 1), 2)
    record("term_months_invalid", len(sel))
    sel = take(8)
    loans.loc[sel, "loan_status"] = "PendingX"
    loans.loc[sel, "delinquency_days"] = 0  # keep the delinquency-consistency check clean
    record("loan_status_invalid", len(sel))
    sel = take(20); loans.loc[sel, "borrower_id"] = [f"B9{i:04d}" for i in range(len(sel))]; record("borrower_dangling", len(sel))
    sel = take(15); loans.loc[sel, "vehicle_id"] = [f"V9{i:04d}" for i in range(len(sel))]; record("vehicle_dangling", len(sel))
    sel = take(10); loans.loc[sel, "dealer_id"] = [f"D9{i:03d}" for i in range(len(sel))]; record("dealer_dangling", len(sel))
    sel = take(120); loans.loc[sel, "last_payment_date"] = [(AS_OF - timedelta(days=rng.randint(60, 150))).isoformat() for _ in sel]; record("stale_last_payment", len(sel))
    sel = take(80); loans.loc[sel, "updated_at"] = [(AS_OF - timedelta(days=rng.randint(70, 200))).isoformat() for _ in sel]; record("stale_updated_at", len(sel))
    sel = take(22); loans.loc[sel, "current_balance"] = loans.loc[sel, "loan_amount"] * 1.25; record("balance_exceeds_loan", len(sel))
    sel = take(14); loans.loc[sel, "down_payment"] = loans.loc[sel, "loan_amount"] * 1.10; record("down_payment_exceeds_loan", len(sel))
    sel = take(30); loans.loc[sel, "maturity_date"] = [_add_months(date.fromisoformat(d), 6).isoformat() for d in loans.loc[sel, "origination_date"]]; record("maturity_mismatch", len(sel))
    sel = take(40)
    half = len(sel) // 2
    loans.loc[sel[:half], "delinquency_days"] = [rng.randint(30, 90) for _ in range(half)]
    loans.loc[sel[:half], "loan_status"] = "Current"
    loans.loc[sel[half:], "delinquency_days"] = 0
    loans.loc[sel[half:], "loan_status"] = "Delinquent"
    record("delinquency_inconsistent", len(sel))
    sel = take(25); loans.loc[sel, "monthly_payment"] = loans.loc[sel, "monthly_payment"] * 1.30; record("payment_amount_off", len(sel))
    sel = take(9); loans.loc[sel, "vehicle_year"] = 1985; record("vehicle_year_out_of_range", len(sel))
    sel = take(11); loans.loc[sel, "annual_income"] = 0.0; record("annual_income_nonpositive", len(sel))
    sel = take(28)
    loans.loc[sel, "next_payment_due_date"] = [(date.fromisoformat(d) - timedelta(days=10)).isoformat() for d in loans.loc[sel, "last_payment_date"]]
    record("due_before_last_payment", len(sel))
    sel = take(7)
    loans.loc[sel, "loan_amount"] = 0.0
    loans.loc[sel, "monthly_payment"] = 0.0
    loans.loc[sel, "current_balance"] = 0.0
    loans.loc[sel, "down_payment"] = 0.0
    record("loan_amount_nonpositive", len(sel))
    sel = take(16); loans.loc[sel, "ltv_ratio"] = 1.35; record("ltv_exceeds_limit", len(sel))

    # duplicate loan rows (10 copies of existing loans, new row positions)
    dup_src = loans.iloc[take(10)].copy()
    loans = pd.concat([loans, dup_src], ignore_index=True)
    record("duplicate_loan_rows", len(dup_src))

    # duplicate VINs (12 vehicles each take the VIN of a distinct other vehicle)
    vsel = rng.sample(list(vehicles.index), 12)
    targets = rng.sample([i for i in vehicles.index if i not in set(vsel)], 12)
    for j, t in zip(vsel, targets):
        vehicles.loc[j, "vin"] = vehicles.loc[t, "vin"]
    record("duplicate_vins", len(vsel))

    # dangling payments + invalid payment rows
    pidx = list(payments.index)
    rng.shuffle(pidx)
    psel = pidx[:25]; payments.loc[psel, "loan_id"] = [f"L9{i:04d}" for i in range(len(psel))]; record("payment_loan_dangling", len(psel))
    psel = pidx[25:45]; payments.loc[psel, "amount_paid"] = -50.0; record("payment_amount_negative", len(psel))
    psel = pidx[45:57]; payments.loc[psel, "payment_status"] = "Unknown"; record("payment_status_invalid", len(psel))

    loans.to_csv(out_dir / "loans.csv", index=False)
    borrowers.to_csv(out_dir / "borrowers.csv", index=False)
    vehicles.to_csv(out_dir / "vehicles.csv", index=False)
    dealers.to_csv(out_dir / "dealers.csv", index=False)
    payments.to_csv(out_dir / "payments.csv", index=False)

    report = {
        "seed": SEED,
        "as_of": AS_OF.isoformat(),
        "rows": {
            "loans": len(loans),
            "borrowers": len(borrowers),
            "vehicles": len(vehicles),
            "dealers": len(dealers),
            "payments": len(payments),
        },
        "defects": defect_counts,
        "note": "All data is synthetic. Defects are injected deliberately on disjoint row sets.",
    }
    return report
