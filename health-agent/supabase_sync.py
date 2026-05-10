"""Daily sync: VPS SQLite → Supabase.

Reads the last N days of health_metrics + workouts from local SQLite,
pivots them into the Supabase schema, and upserts. Designed to run after
the Oura + Whoop pulls each morning so the dashboard always reflects
the latest day.

Convention for daily_metrics columns:
- hrv, rhr, sleep_score, sleep_hours, steps  → Oura (primary, more accurate)
- recovery_score, strain                     → Whoop only
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

from supabase import create_client

from config import DB_PATH
from database import get_db

logger = logging.getLogger(__name__)


# SQLite metric_name → daily_metrics column. Source-specific (preferred provider).
OURA_METRIC_MAP = {
    "hrv_average": "hrv",
    "readiness_resting_heart_rate": "rhr",
    "sleep_score": "sleep_score",
    "total_sleep_seconds": "sleep_hours",  # special-cased: divide by 3600
    "steps": "steps",
}

WHOOP_METRIC_MAP = {
    "recovery_score": "recovery_score",
    "strain_score": "strain",
}


def _supabase():
    import os
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    return create_client(url, key)


def sync(days: int = 7, db_path: Optional[str] = None) -> dict:
    """Push the last `days` of metrics + workouts to Supabase.

    Returns counts of rows synced per table.
    """
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    db_kwargs = {"db_path": db_path} if db_path else {}

    with get_db(**db_kwargs) as conn:
        rows = conn.execute(
            "SELECT date, source, metric_name, value FROM health_metrics "
            "WHERE date >= ? AND value IS NOT NULL "
            "ORDER BY date",
            (cutoff,),
        ).fetchall()

        # Pivot: by_date[YYYY-MM-DD] = {col_name: value}
        by_date: dict[str, dict] = {}
        for r in rows:
            d, src, name, value = r["date"], r["source"], r["metric_name"], r["value"]
            target_map = OURA_METRIC_MAP if src == "oura" else WHOOP_METRIC_MAP if src == "whoop" else {}
            col = target_map.get(name)
            if not col:
                continue

            row = by_date.setdefault(d, {})

            # Special handling for sleep_hours (Oura stores seconds)
            if col == "sleep_hours":
                row["sleep_hours"] = round(value / 3600, 2)
            elif col in ("sleep_score", "recovery_score"):
                row[col] = int(round(value))
            elif col == "steps":
                row[col] = int(value)
            else:
                # hrv, rhr, strain: float
                row[col] = round(value, 2)

        # Compose final rows
        metric_rows = []
        for d, row in by_date.items():
            row["date"] = d
            row["source"] = "merged"
            metric_rows.append(row)

        # Workouts → workouts_strong
        workout_rows = conn.execute(
            "SELECT date, workout_name, exercise, set_order, weight, reps, "
            "volume, estimated_1rm "
            "FROM workouts WHERE date >= ? ORDER BY date, exercise, set_order",
            (cutoff,),
        ).fetchall()

    # Push to Supabase
    sb = _supabase()

    metric_count = 0
    if metric_rows:
        # Chunk to keep payload sane
        for i in range(0, len(metric_rows), 100):
            chunk = metric_rows[i:i + 100]
            sb.table("daily_metrics").upsert(chunk, on_conflict="date").execute()
            metric_count += len(chunk)
        logger.info("Supabase sync: %d daily_metrics rows", metric_count)

    workout_count = 0
    if workout_rows:
        ws = []
        for w in workout_rows:
            ws.append({
                "date": w["date"],
                "workout_name": w["workout_name"],
                "exercise": w["exercise"],
                "set_number": w["set_order"],
                "reps": w["reps"],
                "weight_lbs": w["weight"] or 0,
                "e1rm": round(w["estimated_1rm"] or 0, 1),
                "muscle_group": _infer_group(w["exercise"]),
                "notes": None,
            })
        for i in range(0, len(ws), 200):
            chunk = ws[i:i + 200]
            sb.table("workouts_strong").upsert(chunk).execute()
            workout_count += len(chunk)
        logger.info("Supabase sync: %d workout rows", workout_count)

    return {"daily_metrics": metric_count, "workouts_strong": workout_count}


# Lightweight muscle-group inference (mirrors dashboard/lib/...)
GROUP_RULES = [
    ("squat", "Legs"), ("deadlift", "Back"), ("rdl", "Legs"),
    ("romanian", "Legs"), ("leg ", "Legs"), ("calf", "Legs"),
    ("lunge", "Legs"), ("hip thrust", "Legs"), ("glute", "Legs"),
    ("bench", "Chest"), ("incline", "Chest"), ("decline", "Chest"),
    ("chest fly", "Chest"), ("dip", "Chest"), ("push-up", "Chest"),
    ("pushup", "Chest"),
    ("row", "Back"), ("pull-up", "Back"), ("pull up", "Back"),
    ("pullup", "Back"), ("chin", "Back"), ("lat ", "Back"),
    ("face pull", "Back"), ("shrug", "Back"), ("hyperext", "Back"),
    ("shoulder", "Shoulders"), ("overhead press", "Shoulders"),
    ("ohp", "Shoulders"), ("lateral raise", "Shoulders"),
    ("rear delt", "Shoulders"), ("front raise", "Shoulders"),
    ("arnold", "Shoulders"), ("upright row", "Shoulders"),
    ("curl", "Arms"), ("tricep", "Arms"), ("triceps", "Arms"),
    ("skull", "Arms"), ("pushdown", "Arms"), ("hammer", "Arms"),
    ("plank", "Core"), ("crunch", "Core"), ("ab ", "Core"),
    ("abs", "Core"), ("russian twist", "Core"),
    ("hanging leg", "Core"), ("knee raise", "Core"), ("sit-up", "Core"),
    ("treadmill", "Cardio"), ("running", "Cardio"),
    ("cycling", "Cardio"), ("rowing machine", "Cardio"),
    ("elliptical", "Cardio"), ("stairmaster", "Cardio"),
]


def _infer_group(exercise: str) -> str:
    n = exercise.lower()
    for k, v in GROUP_RULES:
        if k in n:
            return v
    return "Other"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    result = sync(days=7)
    print(f"Synced: {result}")
