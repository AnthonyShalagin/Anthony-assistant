"""Strong app CSV parser.

Parses workout exports from the Strong app, computes volume
and estimated 1RM using the Epley formula.
"""

import csv
import io
import logging
from typing import Optional

from database import get_db, upsert_workout

logger = logging.getLogger(__name__)

# Strong CSV expected columns
EXPECTED_COLUMNS = {
    "Date", "Workout Name", "Exercise Name", "Set Order",
    "Weight", "Reps",
}


def epley_1rm(weight: float, reps: int) -> float:
    """Estimate 1-rep max using the Epley formula.

    Formula: 1RM = weight × (1 + reps / 30)
    Returns 0 if reps <= 0 or weight <= 0.
    """
    if reps <= 0 or weight <= 0:
        return 0.0
    if reps == 1:
        return weight
    return round(weight * (1 + reps / 30), 1)


def compute_volume(weight: float, reps: int) -> float:
    """Compute set volume (weight × reps)."""
    if weight <= 0 or reps <= 0:
        return 0.0
    return round(weight * reps, 1)


def parse_csv(content: str, db_path: Optional[str] = None) -> dict:
    """Parse a Strong CSV export and store workouts in the database.

    Args:
        content: Raw CSV string content.
        db_path: Optional database path override.

    Returns:
        Summary dict with counts and exercise stats.
    """
    reader = csv.DictReader(io.StringIO(content))

    # Validate columns
    if reader.fieldnames:
        missing = EXPECTED_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ValueError(f"CSV missing required columns: {missing}")

    rows = list(reader)
    if not rows:
        return {"sets": 0, "exercises": 0, "workouts": 0}

    exercises = set()
    workouts = set()
    total_sets = 0
    db_kwargs = {"db_path": db_path} if db_path else {}

    with get_db(**db_kwargs) as conn:
        for row in rows:
            try:
                dt = _normalize_date(row.get("Date", ""))
                workout_name = row.get("Workout Name", "").strip()
                exercise = row.get("Exercise Name", "").strip()
                set_order = int(row.get("Set Order", 0))
                weight = float(row.get("Weight", 0) or 0)
                reps = int(row.get("Reps", 0) or 0)

                volume = compute_volume(weight, reps)
                est_1rm = epley_1rm(weight, reps)

                upsert_workout(
                    conn, dt, workout_name, exercise,
                    set_order, weight, reps, volume, est_1rm,
                )
                exercises.add(exercise)
                workouts.add((dt, workout_name))
                total_sets += 1
            except (ValueError, KeyError) as e:
                logger.warning("Skipping malformed row: %s — %s", row, e)

    summary = {
        "sets": total_sets,
        "exercises": len(exercises),
        "workouts": len(workouts),
        "exercise_list": sorted(exercises),
    }
    logger.info(
        "Parsed Strong CSV: %d sets, %d exercises, %d workouts",
        total_sets, len(exercises), len(workouts),
    )
    return summary


def _normalize_date(date_str: str) -> str:
    """Normalize various date formats to ISO format (YYYY-MM-DD)."""
    date_str = date_str.strip().strip('"')
    # Try common formats
    from datetime import datetime
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str, fmt).date().isoformat()
        except ValueError:
            continue
    # Fallback: return as-is and let the caller handle errors
    return date_str.split(" ")[0] if " " in date_str else date_str
