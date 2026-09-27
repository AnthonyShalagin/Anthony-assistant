"""Hevy API client — api-key header authentication (Hevy Pro only).

Anthony logs lifting in Hevy (switched from Strong, Sept 2026). Hevy is one hop
and queryable retroactively, unlike Strong -> Apple Health -> Oura, which only
syncs the current day and silently dropped sessions.

Writes the same metric names Oura does (strength_sessions, strength_minutes)
under source "hevy", plus set-level rows in the workouts table, so the weekly
review and dashboard need no new plumbing.
API docs: https://api.hevyapp.com/docs/
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

import requests

from config import HEVY_API_KEY
from database import get_db, upsert_metric, upsert_workout
from parsers.strong import compute_volume, epley_1rm

logger = logging.getLogger(__name__)

BASE_URL = "https://api.hevyapp.com/v1"
LOCAL_TZ = ZoneInfo("America/New_York")
KG_TO_LB = 2.20462
PAGE_SIZE = 10  # API max
MAX_PAGES = 100


def _get(endpoint: str, params: Optional[dict] = None, api_key: Optional[str] = None) -> dict:
    resp = requests.get(f"{BASE_URL}/{endpoint}",
                        headers={"api-key": api_key or HEVY_API_KEY},
                        params=params or {}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _local_day(ts: str) -> Optional[str]:
    """ISO timestamp (UTC 'Z') -> Eastern calendar date, so a 9pm lift isn't filed tomorrow."""
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(LOCAL_TZ).date().isoformat()
    except (AttributeError, ValueError):
        return None


def _minutes(workout: dict) -> float:
    try:
        start = datetime.fromisoformat(workout["start_time"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(workout["end_time"].replace("Z", "+00:00"))
        return round((end - start).total_seconds() / 60, 1)
    except (KeyError, AttributeError, ValueError):
        return 0.0


def fetch_workouts(start: str, api_key: Optional[str] = None) -> list[dict]:
    """All workouts whose local date is >= start (YYYY-MM-DD).

    The list endpoint is newest first, so paging stops at the first page that
    reaches back past `start`.
    """
    out = []
    for page in range(1, MAX_PAGES + 1):
        try:
            data = _get("workouts", {"page": page, "pageSize": PAGE_SIZE}, api_key)
        except requests.HTTPError as e:
            # Hevy answers 404 for a page past the end
            if e.response is not None and e.response.status_code == 404:
                break
            raise
        workouts = data.get("workouts", [])
        out.extend(w for w in workouts if (_local_day(w.get("start_time")) or "") >= start)
        days = [_local_day(w.get("start_time")) or "" for w in workouts]
        if not workouts or min(days) < start or page >= data.get("page_count", page):
            break
    return out


def _is_working(s: dict) -> bool:
    return s.get("type") != "warmup"


def _is_hard(s: dict) -> bool:
    """Near failure: RPE 8+ or marked failure. The Sept 2026 analysis found no set near failure."""
    return s.get("type") == "failure" or (s.get("rpe") or 0) >= 8


def pull_range(start: str, end: str, api_key: Optional[str] = None,
               db_path: Optional[str] = None) -> dict:
    """Pull Hevy workouts for start..end (inclusive) and store them.

    Every day in the range is written, zeros included, so a rest day reads 0.
    """
    db_kwargs = {"db_path": db_path} if db_path else {}
    d0, d1 = date.fromisoformat(start), date.fromisoformat(end)
    days = {(d0 + timedelta(days=i)).isoformat(): {
                "strength_sessions": 0, "strength_minutes": 0.0,
                "working_sets": 0, "hard_sets": 0, "rpe_logged_sets": 0}
            for i in range((d1 - d0).days + 1)}

    workouts = [w for w in fetch_workouts(start, api_key) if _local_day(w.get("start_time")) in days]
    with get_db(**db_kwargs) as conn:
        for w in workouts:
            day = _local_day(w["start_time"])
            totals = days[day]
            totals["strength_sessions"] += 1
            totals["strength_minutes"] += _minutes(w)
            name = w.get("title") or "Workout"
            for ex in w.get("exercises", []):
                n = 0
                for s in ex.get("sets", []):
                    if not _is_working(s):
                        continue
                    n += 1
                    totals["working_sets"] += 1
                    totals["hard_sets"] += _is_hard(s)
                    totals["rpe_logged_sets"] += s.get("rpe") is not None
                    weight = round((s.get("weight_kg") or 0) * KG_TO_LB, 1)
                    reps = int(s.get("reps") or 0)
                    upsert_workout(conn, day, name, ex.get("title", ""), n, weight, reps,
                                   compute_volume(weight, reps), epley_1rm(weight, reps))
        for d, values in days.items():
            for metric, value in values.items():
                upsert_metric(conn, d, "hevy", metric, value,
                              "minutes" if metric.endswith("minutes") else "count")

    logger.info("Hevy pull %s..%s: %d workouts", start, end, len(workouts))
    return {"workouts": len(workouts), "days": days}


def pull_daily(dt: Optional[str] = None, api_key: Optional[str] = None,
               db_path: Optional[str] = None) -> dict:
    """Re-pull the last 3 days, so late-saved or edited sessions get picked up."""
    target = dt or date.today().isoformat()
    start = (date.fromisoformat(target) - timedelta(days=2)).isoformat()
    try:
        return pull_range(start, target, api_key, db_path)
    except requests.RequestException as e:
        logger.error("Hevy pull failed: %s", e)
        return {"error": str(e)}


def verify_token(api_key: Optional[str] = None) -> bool:
    try:
        _get("user/info", api_key=api_key)
        return True
    except requests.RequestException:
        return False
