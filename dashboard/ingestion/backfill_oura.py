"""One-shot Oura backfill: pulls all available history and upserts to Supabase.

Run with the venv active:
  source venv/bin/activate
  OURA_TOKEN=... SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... python backfill_oura.py
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta

import requests
from supabase import create_client

OURA_BASE = "https://api.ouraring.com/v2/usercollection"


def headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {os.environ['OURA_TOKEN']}"}


def fetch(path: str, start: date, end: date) -> list[dict]:
    """Page through an Oura collection."""
    out: list[dict] = []
    next_token: str | None = None
    while True:
        params = {
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        }
        if next_token:
            params["next_token"] = next_token
        r = requests.get(f"{OURA_BASE}/{path}", headers=headers(), params=params, timeout=30)
        r.raise_for_status()
        body = r.json()
        out.extend(body.get("data", []))
        next_token = body.get("next_token")
        if not next_token:
            break
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=730, help="how many days back to pull (default 2y)")
    args = p.parse_args()

    end = date.today()
    start = end - timedelta(days=args.days)

    print(f"Pulling Oura data from {start} → {end}...")
    sleep = fetch("daily_sleep", start, end)
    activity = fetch("daily_activity", start, end)
    sleep_periods = fetch("sleep", start, end)

    print(f"  daily_sleep: {len(sleep)} rows")
    print(f"  daily_activity: {len(activity)} rows")
    print(f"  sleep periods: {len(sleep_periods)} rows")

    # Build merged daily_metrics rows
    by_date: dict[str, dict] = {}
    sleep_details: dict[str, dict] = {}

    for d in sleep:
        by_date.setdefault(d["day"], {})["sleep_score"] = d.get("score")

    for d in activity:
        row = by_date.setdefault(d["day"], {})
        row["steps"] = d.get("steps")

    # Long sleep periods give HRV, RHR, hours, stages
    for s in sleep_periods:
        if s.get("type") != "long_sleep":
            continue
        day = s["day"]
        row = by_date.setdefault(day, {})
        if s.get("average_hrv") is not None:
            row["hrv"] = round(s["average_hrv"], 1)
        if s.get("average_heart_rate") is not None:
            row["rhr"] = round(s["average_heart_rate"], 1)
        if s.get("total_sleep_duration"):
            row["sleep_hours"] = round(s["total_sleep_duration"] / 3600, 2)

        sleep_details[day] = {
            "date": day,
            "deep_min": (s.get("deep_sleep_duration") or 0) // 60,
            "rem_min": (s.get("rem_sleep_duration") or 0) // 60,
            "light_min": (s.get("light_sleep_duration") or 0) // 60,
            "awake_min": (s.get("awake_time") or 0) // 60,
            "efficiency": s.get("efficiency"),
            "bedtime": s.get("bedtime_start"),
            "wake_time": s.get("bedtime_end"),
        }

    # Compose final rows
    metric_rows = []
    for day, row in by_date.items():
        row["date"] = day
        row["source"] = "oura"
        metric_rows.append(row)

    print(f"  -> {len(metric_rows)} merged daily_metrics, {len(sleep_details)} sleep_detail rows")

    # Upsert
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

    # Chunk to avoid huge payloads
    CHUNK = 500
    for i in range(0, len(metric_rows), CHUNK):
        chunk = metric_rows[i:i + CHUNK]
        sb.table("daily_metrics").upsert(chunk, on_conflict="date").execute()
        print(f"  upserted {i + len(chunk)}/{len(metric_rows)} daily_metrics")

    sleep_list = list(sleep_details.values())
    for i in range(0, len(sleep_list), CHUNK):
        chunk = sleep_list[i:i + CHUNK]
        sb.table("sleep_detail").upsert(chunk, on_conflict="date").execute()
        print(f"  upserted {i + len(chunk)}/{len(sleep_list)} sleep_detail")

    # Spot-check
    res = sb.table("daily_metrics").select("date", count="exact").eq("source", "oura").execute()
    print(f"\nFinal: {res.count} oura daily_metrics rows in DB")


if __name__ == "__main__":
    if "OURA_TOKEN" not in os.environ:
        print("Set OURA_TOKEN, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY in env first.", file=sys.stderr)
        sys.exit(1)
    main()
