"""Tests for the data governance toolkit."""

import csv
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from alerting import alerts_for, dispatch_simulated, simulate_response_times  # noqa: E402
from checks import run_checks  # noqa: E402
from generate_data import generate  # noqa: E402
from run_all import run_sql_checks  # noqa: E402


@pytest.fixture(scope="module")
def data_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("data")
    generate(d)
    return d


@pytest.fixture(scope="module")
def data(data_dir):
    return {t: pd.read_csv(data_dir / f"{t}.csv") for t in ["loans", "borrowers", "vehicles", "dealers", "payments"]}


@pytest.fixture(scope="module")
def scorecard(data):
    return run_checks(data)


def test_generator_is_deterministic(tmp_path_factory):
    d1, d2 = tmp_path_factory.mktemp("a"), tmp_path_factory.mktemp("b")
    r1, r2 = generate(d1), generate(d2)
    assert r1["rows"] == r2["rows"]
    assert r1["defects"] == r2["defects"]
    assert pd.read_csv(d1 / "loans.csv").equals(pd.read_csv(d2 / "loans.csv"))


def test_exactly_25_checks(scorecard):
    assert len(scorecard) == 25
    assert sorted(scorecard["check_id"]) == [f"DQ{i:02d}" for i in range(1, 26)]


def test_scorecard_columns(scorecard):
    expected = {"check_id", "dimension", "table", "field", "rows_checked",
                "violations", "violation_rate", "status", "severity",
                "data_owner", "owner_email"}
    assert expected.issubset(set(scorecard.columns))


def test_injected_defect_counts(scorecard):
    by_id = scorecard.set_index("check_id")["violations"].to_dict()
    assert by_id["DQ02"] == 25   # null credit scores
    assert by_id["DQ04"] == 18   # out-of-range credit scores
    assert by_id["DQ08"] == 10   # duplicate loan rows
    assert by_id["DQ09"] == 12   # duplicate VINs
    assert by_id["DQ10"] == 20   # dangling borrowers
    assert by_id["DQ14"] == 120  # stale last payments
    assert by_id["DQ15"] == 80   # stale updated_at
    assert by_id["DQ18"] == 30   # maturity mismatches
    assert by_id["DQ19"] == 40   # delinquency inconsistencies
    assert by_id["DQ20"] == 25   # amortisation mismatches
    assert by_id["DQ23"] == 32   # invalid payments (20 negative + 12 bad status)
    assert by_id["DQ25"] == 23   # 7 non-positive amounts + 16 LTV breaches
    assert by_id["DQ01"] == 0    # no null loan_ids injected


def test_dimensions_cover_claimed_families(scorecard):
    dims = set(scorecard["dimension"])
    for required in ["Completeness", "Validity", "Uniqueness", "Freshness"]:
        assert required in dims


def test_sql_checks_match_python(data_dir, scorecard):
    sql = run_sql_checks(data_dir)
    merged = scorecard.merge(sql, on="check_id")
    assert len(merged) == 25
    assert (merged["violations"] == merged["sql_violations"]).all()


def test_alerts_match_failed_checks(scorecard, tmp_path):
    alerts = alerts_for(scorecard)
    n_fail = int((scorecard["status"] == "FAIL").sum())
    assert len(alerts) == n_fail
    log = dispatch_simulated(alerts, tmp_path / "alert_log.csv")
    assert (log["sent"] == False).all()  # dispatch is simulated, never sent
    assert set(log["recipient"]) <= set(scorecard["owner_email"])


def test_response_time_simulation_is_honest_and_deterministic():
    sim = simulate_response_times()
    assert sim == simulate_response_times()  # same seed -> same numbers
    assert sim["automated_mean_hours"] < sim["manual_mean_hours"]
    assert sim["automated_same_day_pct"] > sim["manual_same_day_pct"]
    assert sim["n_issues"] == 500


def test_dictionary_covers_60_plus_fields_and_all_columns(data):
    rows = list(csv.DictReader(open(ROOT / "docs" / "data_dictionary.csv")))
    assert len(rows) >= 60
    catalogued = {(r["table"], r["field"]) for r in rows}
    for table, df in data.items():
        for col in df.columns:
            assert (table, col) in catalogued, f"{table}.{col} missing from dictionary"


def test_lineage_metrics_trace_to_real_fields(data):
    text = (ROOT / "docs" / "lineage.md").read_text()
    for field in ["current_balance", "delinquency_days", "credit_score",
                  "interest_rate", "ltv_ratio", "payment_status"]:
        assert field in text


def test_power_automate_flow_is_valid_spec():
    flow = json.loads((ROOT / "docs" / "power-automate-flow.json").read_text())
    assert flow["metadata"]["status"] == "spec"
    assert "Send_email_to_owner" in json.dumps(flow)


def _clean_data():
    loans = pd.DataFrame([{
        "loan_id": "L00001", "borrower_id": "B00001", "vehicle_id": "V00001",
        "dealer_id": "D0001", "origination_date": "2025-01-15",
        "maturity_date": "2030-01-15", "term_months": 60, "loan_amount": 20000.0,
        "down_payment": 4000.0, "interest_rate": 6.0, "monthly_payment": 386.66,
        "current_balance": 15000.0, "vehicle_year": 2024, "vehicle_make": "Toyota",
        "vehicle_model": "Camry", "credit_score": 720, "employment_status": "Employed",
        "annual_income": 80000.0, "state": "IL", "loan_status": "Current",
        "delinquency_days": 0, "last_payment_date": "2026-10-10",
        "next_payment_due_date": "2026-11-10", "origination_channel": "Dealer",
        "co_signer_flag": 0, "loan_purpose": "New Vehicle", "ltv_ratio": 0.8,
        "dti_ratio": 0.2, "created_at": "2025-01-15", "updated_at": "2026-10-12",
    }])
    borrowers = pd.DataFrame([{
        "borrower_id": "B00001", "first_name": "A", "last_name": "B",
        "date_of_birth": "1990-01-01", "state": "IL", "zip_code": "62701",
        "credit_bureau": "Equifax", "email_domain": "example.com",
        "phone_type": "Mobile", "record_created_at": "2024-01-01",
    }])
    vehicles = pd.DataFrame([{
        "vehicle_id": "V00001", "vin": "1" * 17, "make": "Toyota", "model": "Camry",
        "model_year": 2024, "mileage": 10000, "msrp": 25000.0,
        "vehicle_type": "Sedan", "fuel_type": "Gasoline",
    }])
    dealers = pd.DataFrame([{
        "dealer_id": "D0001", "dealer_name": "Dealer 001 Auto Group",
        "state": "IL", "region": "Midwest", "dealer_tier": "Tier 1",
    }])
    payments = pd.DataFrame([{
        "payment_id": "P000001", "loan_id": "L00001", "payment_date": "2026-10-10",
        "amount_due": 386.66, "amount_paid": 386.66, "payment_status": "Completed",
        "payment_method": "ACH", "posted_at": "2026-10-10",
    }])
    return {"loans": loans, "borrowers": borrowers, "vehicles": vehicles,
            "dealers": dealers, "payments": payments}


def test_all_checks_pass_on_clean_data():
    sc = run_checks(_clean_data())
    assert len(sc) == 25
    assert (sc["status"] == "PASS").all(), sc[sc["status"] != "PASS"]
