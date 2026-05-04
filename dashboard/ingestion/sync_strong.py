"""Parse a Strong app CSV export and upsert workouts to Supabase.

Strong CSV columns (current schema):
  Date, Workout Name, Duration, Exercise Name, Set Order, Weight, Reps,
  Distance, Seconds, Notes, Workout Notes, RPE
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path

from db import client, insert_workouts


# Rough mapping from exercise name → muscle group.
GROUP = {
    "squat": "Legs",
    "deadlift": "Back",
    "leg press": "Legs",
    "leg curl": "Legs",
    "leg extension": "Legs",
    "rdl": "Legs",
    "romanian": "Legs",
    "lunge": "Legs",
    "bench": "Chest",
    "incline": "Chest",
    "fly": "Chest",
    "dip": "Chest",
    "row": "Back",
    "pull-up": "Back",
    "pull up": "Back",
    "lat pulldown": "Back",
    "shoulder": "Shoulders",
    "press": "Shoulders",
    "lateral raise": "Shoulders",
    "curl": "Arms",
    "tricep": "Arms",
    "extension": "Arms",
}


def muscle_group(exercise: str) -> str:
    n = exercise.lower()
    for k, v in GROUP.items():
        if k in n:
            return v
    return "Other"


def epley(weight: float, reps: float) -> float:
    if weight <= 0 or reps <= 0:
        return 0.0
    return round(weight * (1 + reps / 30), 1)


def parse(csv_path: Path) -> list[dict]:
    rows: list[dict] = []
    with csv_path.open() as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                weight = float(r.get("Weight") or 0)
                reps = int(float(r.get("Reps") or 0))
            except ValueError:
                continue
            if reps == 0 and weight == 0:
                continue
            date_str = (r.get("Date") or "").split(" ")[0]
            try:
                date_iso = datetime.strptime(date_str, "%Y-%m-%d").date().isoformat()
            except ValueError:
                continue
            exercise = r.get("Exercise Name") or ""
            try:
                set_num = int(float(r.get("Set Order") or 1))
            except ValueError:
                set_num = 1
            rows.append(
                {
                    "date": date_iso,
                    "workout_name": r.get("Workout Name"),
                    "exercise": exercise,
                    "set_number": set_num,
                    "reps": reps,
                    "weight_lbs": weight,
                    "e1rm": epley(weight, reps),
                    "muscle_group": muscle_group(exercise),
                    "notes": r.get("Notes"),
                }
            )
    return rows


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("csv", type=Path)
    args = p.parse_args()
    rows = parse(args.csv)
    sb = client()
    insert_workouts(sb, rows)
    print(f"strong: upserted {len(rows)} sets from {args.csv.name}")


if __name__ == "__main__":
    main()
