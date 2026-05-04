"""One-shot Whoop backfill. Pulls all available cycles + recovery + sleep
records and merges into Supabase daily_metrics.

Run with the venv active:
  source venv/bin/activate
  WHOOP_CLIENT_ID=... WHOOP_CLIENT_SECRET=... WHOOP_REFRESH_TOKEN=... \
  SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... python backfill_whoop.py
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

import requests
from supabase import create_client

WHOOP_BASE = "https://api.prod.whoop.com/developer/v2"


def access_token() -> tuple[str, str]:
    """Refresh and return (access_token, new_refresh_token)."""
    r = requests.post(
        "https://api.prod.whoop.com/oauth/oauth2/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": os.environ["WHOOP_REFRESH_TOKEN"],
            "client_id": os.environ["WHOOP_CLIENT_ID"],
            "client_secret": os.environ["WHOOP_CLIENT_SECRET"],
            "scope": "offline read:recovery read:cycles read:sleep read:workout read:profile",
        },
        timeout=20,
    )
    r.raise_for_status()
    body = r.json()
    return body["access_token"], body.get("refresh_token", "")


def fetch(token: str, path: str, start: datetime, end: datetime, limit: int = 25) -> list[dict]:
    """Page through a Whoop collection."""
    out: list[dict] = []
    next_token: str | None = None
    while True:
        params: dict[str, str] = {
            "start": start.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "end": end.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "limit": str(limit),
        }
        if next_token:
            params["nextToken"] = next_token  # Whoop wants camelCase
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


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=730, help="how many days back to pull (default 2y)")
    args = p.parse_args()

    print("Refreshing Whoop access token...")
    tok, new_refresh = access_token()
    # Save the rotated refresh token IMMEDIATELY so a later crash can't
    # leave us with a consumed (and unusable) token.
    if new_refresh:
        env_path = os.path.expanduser(
            "~/Anthony-assistant/.claude/worktrees/sweet-mcclintock-5642ec/dashboard/.env.local"
        )
        if os.path.exists(env_path):
            import re
            with open(env_path) as f:
                text = f.read()
            text = re.sub(r"WHOOP_REFRESH_TOKEN=.*", f"WHOOP_REFRESH_TOKEN={new_refresh}", text)
            with open(env_path, "w") as f:
                f.write(text)
            print("  ✓ rotated refresh_token saved to .env.local")

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=args.days)
    print(f"Pulling Whoop data from {start.date()} → {end.date()}...")

    cycles = fetch(tok, "cycle", start, end)
    recoveries = fetch(tok, "recovery", start, end)
    sleeps = fetch(tok, "activity/sleep", start, end)

    print(f"  cycles: {len(cycles)}")
    print(f"  recoveries: {len(recoveries)}")
    print(f"  sleeps: {len(sleeps)}")

    by_date: dict[str, dict] = {}

    for c in cycles:
        day = (c.get("start") or "")[:10]
        if not day:
            continue
        score = c.get("score") or {}
        row = by_date.setdefault(day, {})
        if score.get("strain") is not None:
            row["strain"] = round(score["strain"], 2)

    for rec in recoveries:
        # cycle date or created_at
        day = (rec.get("created_at") or "")[:10]
        if not day:
            continue
        score = rec.get("score") or {}
        row = by_date.setdefault(day, {})
        if score.get("recovery_score") is not None:
            row["recovery_score"] = int(round(score["recovery_score"]))
        if score.get("hrv_rmssd_milli") is not None:
            row["hrv"] = round(score["hrv_rmssd_milli"], 1)
        if score.get("resting_heart_rate") is not None:
            row["rhr"] = round(score["resting_heart_rate"], 1)

    for s in sleeps:
        if s.get("nap"):
            continue
        day = (s.get("start") or "")[:10]
        if not day:
            continue
        score = s.get("score") or {}
        stage = score.get("stage_summary") or {}
        row = by_date.setdefault(day, {})
        if score.get("sleep_performance_percentage") is not None:
            # smallint column — must be int
            row["sleep_score"] = int(round(score["sleep_performance_percentage"]))
        if stage.get("total_in_bed_time_milli"):
            row["sleep_hours"] = round(stage["total_in_bed_time_milli"] / 3_600_000, 2)

    metric_rows = []
    for day, row in by_date.items():
        row["date"] = day
        # Don't overwrite oura's source label; let merging at DB level (upsert)
        # decide.  We tag rows that come from Whoop as 'whoop' for traceability.
        row["source"] = "whoop"
        metric_rows.append(row)
    print(f"  -> {len(metric_rows)} merged daily rows")

    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

    # Upsert in chunks. Whoop fields fill in gaps where Oura didn't report
    # (recovery_score, strain), and overlap with hrv/rhr (Whoop tends to be
    # more accurate during sleep events). We let Whoop override matching keys.
    CHUNK = 500
    for i in range(0, len(metric_rows), CHUNK):
        chunk = metric_rows[i:i + CHUNK]
        # Upsert merges on `date` PK. Existing oura columns stay unless we
        # provide a value, in which case they get overwritten.
        sb.table("daily_metrics").upsert(chunk, on_conflict="date").execute()
        print(f"  upserted {i + len(chunk)}/{len(metric_rows)}")

    # Persist the rotated refresh token to .env.local so the next run uses it
    if new_refresh:
        env_path = os.path.expanduser(
            "~/Anthony-assistant/.claude/worktrees/sweet-mcclintock-5642ec/dashboard/.env.local"
        )
        if os.path.exists(env_path):
            import re
            with open(env_path) as f:
                text = f.read()
            text = re.sub(r"WHOOP_REFRESH_TOKEN=.*", f"WHOOP_REFRESH_TOKEN={new_refresh}", text)
            with open(env_path, "w") as f:
                f.write(text)
            print("  ✓ rotated WHOOP_REFRESH_TOKEN saved to .env.local")

    # Final count
    res = (
        sb.table("daily_metrics")
        .select("date", count="exact")
        .not_.is_("recovery_score", "null")
        .execute()
    )
    print(f"\nFinal: {res.count} rows in daily_metrics with a Whoop recovery_score")


if __name__ == "__main__":
    for k in ("WHOOP_CLIENT_ID", "WHOOP_CLIENT_SECRET", "WHOOP_REFRESH_TOKEN", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
        if k not in os.environ:
            print(f"Missing {k}", file=sys.stderr)
            sys.exit(1)
    main()
