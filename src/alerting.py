"""Alerting: the Python implementation of the Power Automate flow spec.

What this module does (and does not do):

* It implements the alert *logic* from ``docs/power-automate-flow.json``:
  every failed check produces one alert addressed to that check's data
  owner, with its severity and violation counts.
* Dispatch is SIMULATED. No email is sent. Each alert is appended to
  ``outputs/alert_log.csv`` and printed as a ``[SIMULATED EMAIL]`` line,
  so the workflow can be tested end to end without an Outlook connector
  or a real mailbox. Wiring the same payload into the Power Automate
  "Send an email (V2)" action is a configuration step, not a code change
  (see the flow spec).
* ``simulate_response_times`` is a controlled SIMULATION of issue
  response time, not a production measurement. It compares two patterns
  over the same synthetic issue stream (see the docstring).
"""

from __future__ import annotations

import random
import statistics
from pathlib import Path

import pandas as pd


def alerts_for(scorecard: pd.DataFrame) -> list[dict]:
    """One alert dict per failed check, ordered by severity then check_id."""
    sev_rank = {"Critical": 0, "High": 1, "Medium": 2}
    failed = scorecard[scorecard["status"] == "FAIL"].copy()
    failed["rank"] = failed["severity"].map(sev_rank)
    failed = failed.sort_values(["rank", "check_id"])
    alerts = []
    for _, r in failed.iterrows():
        alerts.append(
            {
                "check_id": r["check_id"],
                "dimension": r["dimension"],
                "table": r["table"],
                "field": r["field"],
                "violations": int(r["violations"]),
                "violation_rate": float(r["violation_rate"]),
                "severity": r["severity"],
                "data_owner": r["data_owner"],
                "recipient": r["owner_email"],
                "subject": f"[Data Quality {r['severity']}] {r['check_id']} failed: "
                f"{int(r['violations'])} violations on {r['table']}.{r['field']}",
                "body": (
                    f"Data quality check {r['check_id']} ({r['dimension']}) on "
                    f"{r['table']}.{r['field']} found {int(r['violations'])} violations "
                    f"({float(r['violation_rate']):.2%} of rows checked). "
                    f"See the Power BI data quality scorecard for details."
                ),
            }
        )
    return alerts


def dispatch_simulated(alerts: list[dict], log_path: Path) -> pd.DataFrame:
    """Log each alert as a simulated email dispatch (no mail is sent)."""
    rows = []
    for a in alerts:
        print(f"[SIMULATED EMAIL] To: {a['recipient']} | {a['subject']}")
        rows.append({**a, "dispatch": "simulated", "sent": False})
    df = pd.DataFrame(rows)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(log_path, index=False)
    return df


def simulate_response_times(n_issues: int = 500, seed: int = 7) -> dict:
    """Simulate issue response time: manual review vs automated alerts.

    Same synthetic issue stream, two handling patterns:

    * Manual pattern (the old workflow): issues pile up until the next
      scheduled review, which runs every 3 days, so the wait is
      Uniform(0, 72h); triage then takes Uniform(8, 24h).
    * Automated pattern: the alert fires the moment the check fails, so
      acknowledgement is Exponential(mean 2h) and triage is Uniform(1, 4h).

    "Response time" here means time from issue occurrence to first
    owner acknowledgement + triage — it is NOT full remediation time,
    and it is a simulation, not a production measurement. "Same day"
    means resolved within 24 hours of occurrence.
    """
    rng = random.Random(seed)
    manual, automated = [], []
    for _ in range(n_issues):
        manual.append(rng.uniform(0, 72) + rng.uniform(8, 24))
        automated.append(rng.expovariate(1 / 2.0) + rng.uniform(1, 4))
    m_mean = statistics.mean(manual)
    a_mean = statistics.mean(automated)
    return {
        "n_issues": n_issues,
        "seed": seed,
        "manual_mean_hours": round(m_mean, 2),
        "manual_median_hours": round(statistics.median(manual), 2),
        "manual_same_day_pct": round(100 * sum(h <= 24 for h in manual) / n_issues, 1),
        "automated_mean_hours": round(a_mean, 2),
        "automated_median_hours": round(statistics.median(automated), 2),
        "automated_same_day_pct": round(100 * sum(h <= 24 for h in automated) / n_issues, 1),
        "improvement_factor": round(m_mean / a_mean, 1),
        "manual_mean_days": round(m_mean / 24, 2),
        "automated_mean_days": round(a_mean / 24, 2),
        "definition": "Time from issue occurrence to owner acknowledgement + triage; "
        "simulation only, not a production measurement.",
    }
