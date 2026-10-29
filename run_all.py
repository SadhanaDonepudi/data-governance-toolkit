"""End-to-end reproducible run.

1. Generate the synthetic loan portfolio (data/, git-ignored).
2. Run all 25 Python checks -> outputs/scorecard.csv.
3. Run the 25 SQL checks against SQLite -> outputs/sql_check_results.csv,
   and verify every count matches the Python run.
4. Dispatch simulated owner alerts -> outputs/alert_log.csv.
5. Run the response-time simulation -> outputs/response_time_simulation.json.
6. Write outputs/run_summary.json with the headline numbers the README quotes.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from alerting import alerts_for, dispatch_simulated, simulate_response_times  # noqa: E402
from checks import run_checks  # noqa: E402
from generate_data import generate  # noqa: E402


def run_sql_checks(data_dir: Path) -> pd.DataFrame:
    con = sqlite3.connect(":memory:")
    for table in ["loans", "borrowers", "vehicles", "dealers", "payments"]:
        pd.read_csv(data_dir / f"{table}.csv").to_sql(table, con, index=False)
    sql = (ROOT / "sql" / "checks.sql").read_text()
    rows = con.execute(sql).fetchall()
    con.close()
    return pd.DataFrame(rows, columns=["check_id", "sql_violations"])


def main() -> None:
    data_dir = ROOT / "data"
    out_dir = ROOT / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)

    report = generate(data_dir)
    (out_dir / "generation_report.json").write_text(json.dumps(report, indent=2))

    data = {t: pd.read_csv(data_dir / f"{t}.csv") for t in ["loans", "borrowers", "vehicles", "dealers", "payments"]}
    scorecard = run_checks(data)
    scorecard.to_csv(out_dir / "scorecard.csv", index=False)

    sql_results = run_sql_checks(data_dir)
    merged = scorecard.merge(sql_results, on="check_id")
    merged["sql_matches_python"] = merged["violations"] == merged["sql_violations"]
    merged.to_csv(out_dir / "sql_check_results.csv", index=False)
    mismatches = merged[~merged["sql_matches_python"]]
    if len(mismatches):
        print("WARNING: SQL/Python count mismatches:")
        print(mismatches[["check_id", "violations", "sql_violations"]].to_string(index=False))

    alerts = alerts_for(scorecard)
    dispatch_simulated(alerts, out_dir / "alert_log.csv")

    sim = simulate_response_times()
    (out_dir / "response_time_simulation.json").write_text(json.dumps(sim, indent=2))

    n_pass = int((scorecard["status"] == "PASS").sum())
    summary = {
        "n_checks": len(scorecard),
        "n_pass": n_pass,
        "n_fail": len(scorecard) - n_pass,
        "dq_score_pct": round(100 * n_pass / len(scorecard), 1),
        "total_violations": int(scorecard["violations"].sum()),
        "sql_matches_python": bool(merged["sql_matches_python"].all()),
        "n_alerts_simulated": len(alerts),
        "response_time_simulation": sim,
        "rows": report["rows"],
    }
    (out_dir / "run_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
