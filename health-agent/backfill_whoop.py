"""Re-pull the last N days of Whoop data.

    .venv/bin/python backfill_whoop.py [days]    # default 14

Use after a Whoop re-login to fill the gap while the token was dead. Pulls
oldest first with strict=True, so a day Whoop has no record for stays empty
instead of inheriting the newest recovery. Safe to re-run (upserts).
"""

import sys
from datetime import date, timedelta

from clients.whoop import pull_daily


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
        try:
            summary = pull_daily(day, strict=True)
        except Exception as e:
            failures += 1
            print(f"{day}  FAILED: {type(e).__name__}: {e}")
            continue
        errors = [k for k in summary if k.endswith("_error")]
        if errors:
            failures += 1
        print(f"{day}  recovery={summary.get('recovery_score')}  "
              f"strain={summary.get('strain_score')}  "
              f"sleep={summary.get('sleep_performance')}"
              + (f"  ERRORS: {', '.join(errors)}" if errors else ""))

    print(f"Done. {days + 1} days pulled, {failures} with errors.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
