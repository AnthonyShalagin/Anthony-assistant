"""Re-pull the last N days of Oura data.

    .venv/bin/python backfill_oura.py [days]     # default 14

Use after a fix to the Oura client, or when a day looks wrong. Pulls oldest
first and prints the stored steps per day so a bad pull is obvious. Safe to
re-run: every write is an upsert keyed on (date, source, metric).

This exists because the same thing as a `python -c` one-liner wraps in a
terminal and dies on an IndentationError.
"""

import sys
from datetime import date, timedelta

from clients.oura import pull_daily


def main(argv: list[str]) -> int:
    days = 14
    if len(argv) > 1:
        try:
            days = int(argv[1])
        except ValueError:
            print(f"Usage: {argv[0]} [days]", file=sys.stderr)
            return 1
    if not 1 <= days <= 180:
        print("days must be between 1 and 180", file=sys.stderr)
        return 1

    today = date.today()
    failures = 0
    for i in range(days, -1, -1):
        day = (today - timedelta(days=i)).isoformat()
        summary = pull_daily(day)
        errors = [k for k in summary if k.endswith("_error")]
        if errors:
            failures += 1
        print(f"{day}  steps={summary.get('steps')}  "
              f"sleep={summary.get('sleep_score')}  "
              f"workouts={(summary.get('workouts') or {}).get(day, {}).get('workout_count')}"
              + (f"  ERRORS: {', '.join(errors)}" if errors else ""))

    print(f"Done. {days + 1} days pulled, {failures} with errors.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
