"""Pull Whoop v2 recovery/strain/sleep and upsert to Supabase.

Reuses the token-refresh logic from health-agent/ if present. Whoop API
sends credentials in the body (not Basic auth) — see CLAUDE.md gotcha.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HEALTH_AGENT = Path(__file__).resolve().parents[2] / "health-agent"
if HEALTH_AGENT.exists():
    sys.path.insert(0, str(HEALTH_AGENT))

import requests
from db import client, upsert_daily_metric


WHOOP_BASE = "https://api.prod.whoop.com/developer/v2"


def access_token() -> str:
    """Refresh access token using the body-credentials flow (NOT Basic auth)."""
    refresh = os.environ["WHOOP_REFRESH_TOKEN"]
    client_id = os.environ["WHOOP_CLIENT_ID"]
    secret = os.environ["WHOOP_CLIENT_SECRET"]
    r = requests.post(
        "https://api.prod.whoop.com/oauth/oauth2/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh,
            "client_id": client_id,
            "client_secret": secret,
            "scope": "offline read:recovery read:cycles read:sleep read:workout read:profile",
        },
        timeout=20,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def fetch(token: str, path: str, start: datetime, end: datetime) -> list[dict]:
    """Page through a Whoop collection."""
    out: list[dict] = []
    next_token: str | None = None
    while True:
        params = {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "limit": 25,
        }
        if next_token:
            params["nextToken"] = next_token
        r = requests.get(
            f"{WHOOP_BASE}/{path}",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=30,
        )
        r.raise_for_status()
        body = r.json()
        out.extend(body.get("records", []))
        next_token = body.get("next_token")
        if not next_token:
            break
    return out


def sync(days: int) -> int:
    token = access_token()
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    sb = client()

    cycles = fetch(token, "cycle", start, end)
    recoveries = fetch(token, "recovery", start, end)
    sleeps = fetch(token, "activity/sleep", start, end)

    by_date: dict[str, dict] = {}

    for c in cycles:
        day = c["start"][:10]
        row = by_date.setdefault(day, {})
        row["strain"] = c.get("score", {}).get("strain")

    for r in recoveries:
        # Use the cycle's day
        day = r.get("created_at", "")[:10]
        if not day:
            continue
        row = by_date.setdefault(day, {})
        score = r.get("score", {})
        row["recovery_score"] = score.get("recovery_score")
        if score.get("hrv_rmssd_milli") is not None:
            row["hrv"] = round(score["hrv_rmssd_milli"], 1)
        if score.get("resting_heart_rate") is not None:
            row["rhr"] = score["resting_heart_rate"]

    for s in sleeps:
        if s.get("nap"):
            continue
        day = s["start"][:10]
        row = by_date.setdefault(day, {})
        score = s.get("score", {})
        if score.get("sleep_performance_percentage") is not None:
            row["sleep_score"] = round(score["sleep_performance_percentage"])
        stage = score.get("stage_summary", {})
        if stage.get("total_in_bed_time_milli"):
            row["sleep_hours"] = round(stage["total_in_bed_time_milli"] / 3_600_000, 1)

    written = 0
    for day, row in by_date.items():
        row["date"] = day
        # Don't overwrite Oura source if it already wrote — keep Whoop as supplement.
        row.setdefault("source", "whoop")
        upsert_daily_metric(sb, row)
        written += 1
    return written


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=7)
    args = p.parse_args()
    n = sync(args.days)
    print(f"whoop: upserted {n} days")


if __name__ == "__main__":
    main()
