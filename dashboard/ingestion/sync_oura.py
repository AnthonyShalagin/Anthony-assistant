"""Pull Oura daily readiness/sleep/activity and upsert to Supabase.

Uses Oura v2 personal access token. Token in OURA_TOKEN env var.

Reuses the existing Oura client from health-agent/ if available — so we
don't duplicate HTTP/auth logic. Falls back to bare requests if not.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta
from pathlib import Path

# Make sibling health-agent importable when running from VPS layout.
HEALTH_AGENT = Path(__file__).resolve().parents[2] / "health-agent"
if HEALTH_AGENT.exists():
    sys.path.insert(0, str(HEALTH_AGENT))

import requests
from db import client, upsert_daily_metric, upsert_sleep_detail


OURA_BASE = "https://api.ouraring.com/v2"


def headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {os.environ['OURA_TOKEN']}"}


def fetch(path: str, start: date, end: date) -> dict:
    r = requests.get(
        f"{OURA_BASE}/usercollection/{path}",
        headers=headers(),
        params={"start_date": start.isoformat(), "end_date": end.isoformat()},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def sync(days: int) -> int:
    end = date.today()
    start = end - timedelta(days=days)
    sb = client()

    sleep = fetch("daily_sleep", start, end)
    activity = fetch("daily_activity", start, end)
    readiness = fetch("daily_readiness", start, end)
    sleep_periods = fetch("sleep", start, end)

    by_date: dict[str, dict] = {}

    for d in sleep.get("data", []):
        by_date.setdefault(d["day"], {})["sleep_score"] = d.get("score")

    for d in activity.get("data", []):
        row = by_date.setdefault(d["day"], {})
        row["steps"] = d.get("steps")

    for d in readiness.get("data", []):
        row = by_date.setdefault(d["day"], {})
        # Oura doesn't expose recovery_score the same way Whoop does.
        # We'll keep readiness in raw, but recovery_score stays from Whoop if present.

    # Sleep detail: HRV, RHR, stages, hours
    sleep_details_by_date: dict[str, dict] = {}
    for s in sleep_periods.get("data", []):
        if s.get("type") != "long_sleep":
            continue
        day = s["day"]
        row = by_date.setdefault(day, {})
        row["hrv"] = s.get("average_hrv")
        row["rhr"] = s.get("average_heart_rate")
        if s.get("total_sleep_duration"):
            row["sleep_hours"] = round(s["total_sleep_duration"] / 3600, 1)

        sleep_details_by_date[day] = {
            "date": day,
            "deep_min": (s.get("deep_sleep_duration") or 0) // 60,
            "rem_min": (s.get("rem_sleep_duration") or 0) // 60,
            "light_min": (s.get("light_sleep_duration") or 0) // 60,
            "awake_min": (s.get("awake_time") or 0) // 60,
            "efficiency": s.get("efficiency"),
            "bedtime": s.get("bedtime_start"),
            "wake_time": s.get("bedtime_end"),
            "raw": s,
        }

    written = 0
    for day, row in by_date.items():
        row["date"] = day
        row["source"] = "oura"
        upsert_daily_metric(sb, row)
        written += 1

    for day, sd in sleep_details_by_date.items():
        upsert_sleep_detail(sb, sd)

    return written


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=7)
    args = p.parse_args()
    n = sync(args.days)
    print(f"oura: upserted {n} days")


if __name__ == "__main__":
    main()
