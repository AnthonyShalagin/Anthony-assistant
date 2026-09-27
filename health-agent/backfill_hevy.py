"""Re-pull the last N days of Hevy workouts.

    .venv/bin/python backfill_hevy.py [days]     # default 30

Hevy's API is retroactive, so this can fill any gap, including sessions
imported from Strong. Safe to re-run: every write is an upsert. Prints one
line per day with a session so a bad pull is obvious.
"""

import sys
from datetime import date, timedelta

from clients.hevy import pull_range


def main(argv: list[str]) -> int:
    days = 30
    if len(argv) > 1:
        try:
            days = int(argv[1])
        except ValueError:
            print(f"Usage: {argv[0]} [days]", file=sys.stderr)
            return 1
    if not 1 <= days <= 1500:
        print("days must be between 1 and 1500", file=sys.stderr)
        return 1

    today = date.today()
    result = pull_range((today - timedelta(days=days)).isoformat(), today.isoformat())
    for day, v in result["days"].items():
        if v["strength_sessions"]:
            print(f"{day}  sessions={v['strength_sessions']}  minutes={v['strength_minutes']}  "
                  f"sets={v['working_sets']}  hard={v['hard_sets']}  rpe_logged={v['rpe_logged_sets']}")
    print(f"Done. {result['workouts']} workouts over {days + 1} days.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
