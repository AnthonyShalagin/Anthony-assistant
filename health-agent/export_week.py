"""Print recent health metrics as JSON for the Life OS weekly review.

    python3 export_week.py --days 14 [--db PATH]

Called over ssh from Anthony's Mac. Read-only (the DB is opened with mode=ro)
and stdlib only, so it runs outside the Docker image. Garmin is left out on
purpose: it isn't worn enough to be worth reporting.
"""

import argparse
import json
import os
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

DEFAULT_DB = os.environ.get("DB_PATH") or str(Path(__file__).resolve().parent / "data" / "health.db")
SOURCES = ("oura", "whoop")


def export(db_path: str, days: int, today: Optional[date] = None) -> dict:
    today = today or date.today()
    start = (today - timedelta(days=days)).isoformat()
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        placeholders = ",".join("?" for _ in SOURCES)
        rows = conn.execute(
            f"SELECT date, source, metric_name, value FROM health_metrics "
            f"WHERE date >= ? AND source IN ({placeholders}) ORDER BY date",
            (start, *SOURCES),
        ).fetchall()
        metrics: dict = {}
        for r in rows:
            metrics.setdefault(r["date"], {}).setdefault(r["source"], {})[r["metric_name"]] = r["value"]

        last = {}
        for src in SOURCES:
            row = conn.execute(
                "SELECT MAX(date) AS last_date, MAX(recorded_at) AS last_pull "
                "FROM health_metrics WHERE source = ?",
                (src,),
            ).fetchone()
            last[src] = {"last_data_date": row["last_date"], "last_pull_utc": row["last_pull"]}

        # Set-level Strong detail only exists when a CSV was uploaded.
        strong_csv = conn.execute("SELECT MAX(date) AS d FROM workouts").fetchone()["d"]
    finally:
        conn.close()

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "days": days,
        "metrics_by_date": metrics,
        "last_sync": last,
        "strong_csv_last_workout_date": strong_csv,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--db", default=DEFAULT_DB)
    args = parser.parse_args()
    print(json.dumps(export(args.db, args.days)))


if __name__ == "__main__":
    main()
