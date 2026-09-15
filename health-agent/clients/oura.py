"""Oura Ring API client — bearer token authentication.

Fetches sleep, readiness, activity, and HRV data.
API docs: https://cloud.ouraring.com/v2/docs
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional

import requests

from config import OURA_TOKEN
from database import get_db, upsert_metric

logger = logging.getLogger(__name__)

BASE_URL = "https://api.ouraring.com/v2/usercollection"


def _headers(token: Optional[str] = None) -> dict:
    return {"Authorization": f"Bearer {token or OURA_TOKEN}"}


def _get(endpoint: str, params: dict, token: Optional[str] = None) -> dict:
    """Make an authenticated GET request to Oura API."""
    url = f"{BASE_URL}/{endpoint}"
    resp = requests.get(url, headers=_headers(token), params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_sleep(dt: Optional[str] = None, token: Optional[str] = None) -> list[dict]:
    """Fetch sleep data for a date."""
    target = dt or date.today().isoformat()
    next_day = (date.fromisoformat(target) + timedelta(days=1)).isoformat()
    data = _get("daily_sleep", {"start_date": target, "end_date": next_day}, token)
    return data.get("data", [])


def fetch_readiness(dt: Optional[str] = None, token: Optional[str] = None) -> list[dict]:
    """Fetch readiness data for a date."""
    target = dt or date.today().isoformat()
    next_day = (date.fromisoformat(target) + timedelta(days=1)).isoformat()
    data = _get("daily_readiness", {"start_date": target, "end_date": next_day}, token)
    return data.get("data", [])


def fetch_activity(dt: Optional[str] = None, token: Optional[str] = None) -> list[dict]:
    """Fetch activity data for a date."""
    target = dt or date.today().isoformat()
    next_day = (date.fromisoformat(target) + timedelta(days=1)).isoformat()
    data = _get("daily_activity", {"start_date": target, "end_date": next_day}, token)
    return data.get("data", [])


def fetch_workouts(start: str, end: str, token: Optional[str] = None) -> list[dict]:
    """Fetch workouts between two dates.

    Strong writes each session to Apple Health and Oura imports it from there,
    so this is how strength training arrives without a CSV export.
    """
    data = _get("workout", {"start_date": start, "end_date": end}, token)
    return data.get("data", [])


def _is_strength(workout: dict) -> bool:
    activity = (workout.get("activity") or "").lower()
    return "strength" in activity or "weight" in activity


def _minutes(workout: dict) -> float:
    try:
        start = datetime.fromisoformat(workout["start_datetime"])
        end = datetime.fromisoformat(workout["end_datetime"])
        return round((end - start).total_seconds() / 60, 1)
    except (KeyError, TypeError, ValueError):
        return 0.0


def fetch_hrv(dt: Optional[str] = None, token: Optional[str] = None) -> list[dict]:
    """Fetch HRV data for a date."""
    target = dt or date.today().isoformat()
    next_day = (date.fromisoformat(target) + timedelta(days=1)).isoformat()
    data = _get("daily_hrv", {"start_date": target, "end_date": next_day}, token)
    return data.get("data", [])


def pull_daily(dt: Optional[str] = None, token: Optional[str] = None, db_path: Optional[str] = None) -> dict:
    """Pull all Oura metrics for a date and store in DB.

    Returns a summary dict of what was stored.
    """
    target = dt or date.today().isoformat()
    summary = {}
    db_kwargs = {"db_path": db_path} if db_path else {}

    with get_db(**db_kwargs) as conn:
        # Sleep
        try:
            sleep_data = fetch_sleep(target, token)
            if sleep_data:
                s = sleep_data[0]
                contributors = s.get("contributors", {})
                metrics = {
                    "sleep_score": s.get("score"),
                    "sleep_efficiency": contributors.get("efficiency"),
                    "sleep_latency": contributors.get("latency"),
                    "sleep_restfulness": contributors.get("restfulness"),
                    "total_sleep_duration": s.get("timestamp") and None,  # placeholder
                }
                # Extract total sleep if available in nested data
                if "total_sleep_duration" in s:
                    metrics["total_sleep_duration"] = s["total_sleep_duration"]
                for name, value in metrics.items():
                    if value is not None:
                        upsert_metric(conn, target, "oura", name, value, "score" if "score" in name else "seconds")
                        summary[name] = value
        except requests.RequestException as e:
            logger.error("Oura sleep fetch failed: %s", e)
            summary["sleep_error"] = str(e)

        # Readiness
        try:
            readiness_data = fetch_readiness(target, token)
            if readiness_data:
                r = readiness_data[0]
                score = r.get("score")
                if score is not None:
                    upsert_metric(conn, target, "oura", "readiness_score", score, "score")
                    summary["readiness_score"] = score
                contributors = r.get("contributors", {})
                for key in ("activity_balance", "body_temperature", "hrv_balance",
                            "recovery_index", "resting_heart_rate", "sleep_balance"):
                    val = contributors.get(key)
                    if val is not None:
                        upsert_metric(conn, target, "oura", f"readiness_{key}", val, "score")
                        summary[f"readiness_{key}"] = val
        except requests.RequestException as e:
            logger.error("Oura readiness fetch failed: %s", e)
            summary["readiness_error"] = str(e)

        # Activity: yesterday and today. The pull runs mid-morning, so today's
        # row only has a few hundred steps; re-pulling yesterday overwrites its
        # early-morning snapshot with the finished day. Without this every
        # stored day looked like ~200 steps.
        try:
            yesterday = (date.fromisoformat(target) - timedelta(days=1)).isoformat()
            next_day = (date.fromisoformat(target) + timedelta(days=1)).isoformat()
            activity_data = _get("daily_activity",
                                 {"start_date": yesterday, "end_date": next_day}, token).get("data", [])
            for a in activity_data:
                day = a.get("day") or target
                if day not in (yesterday, target):
                    continue
                values = {"activity_score": (a.get("score"), "score")}
                for key in ("active_calories", "steps", "equivalent_walking_distance"):
                    unit = "kcal" if "calories" in key else ("steps" if key == "steps" else "meters")
                    values[key] = (a.get(key), unit)
                for name, (val, unit) in values.items():
                    if val is None:
                        continue
                    upsert_metric(conn, day, "oura", name, val, unit)
                    if day == target:
                        summary[name] = val
        except requests.RequestException as e:
            logger.error("Oura activity fetch failed: %s", e)
            summary["activity_error"] = str(e)

        # HRV
        try:
            hrv_data = fetch_hrv(target, token)
            if hrv_data:
                h = hrv_data[0]
                for key in ("breath_average", "heart_rate_average", "hrv_average",
                            "temperature_deviation"):
                    val = h.get(key)
                    if val is not None:
                        unit = {"breath_average": "brpm", "heart_rate_average": "bpm",
                                "hrv_average": "ms", "temperature_deviation": "°C"}.get(key, "")
                        upsert_metric(conn, target, "oura", key, val, unit)
                        summary[key] = val
        except requests.RequestException as e:
            logger.error("Oura HRV fetch failed: %s", e)
            summary["hrv_error"] = str(e)

        # Workouts: yesterday and today. The pull runs mid-morning, so an evening
        # session only shows up on the next day's run. Every day in the window is
        # written, zeros included, so a rest day reads as 0 rather than missing.
        try:
            yesterday = (date.fromisoformat(target) - timedelta(days=1)).isoformat()
            next_day = (date.fromisoformat(target) + timedelta(days=1)).isoformat()
            days = {d: {"workout_count": 0, "workout_minutes": 0.0,
                        "strength_sessions": 0, "strength_minutes": 0.0}
                    for d in (yesterday, target)}
            for w in fetch_workouts(yesterday, next_day, token):
                day = days.get(w.get("day"))
                if day is None:
                    continue
                mins = _minutes(w)
                day["workout_count"] += 1
                day["workout_minutes"] += mins
                if _is_strength(w):
                    day["strength_sessions"] += 1
                    day["strength_minutes"] += mins
            for d, values in days.items():
                for name, value in values.items():
                    upsert_metric(conn, d, "oura", name, value,
                                  "minutes" if name.endswith("minutes") else "count")
            summary["workouts"] = days
        except requests.RequestException as e:
            logger.error("Oura workout fetch failed: %s", e)
            summary["workout_error"] = str(e)

    logger.info("Oura pull complete for %s: %d metrics", target, len(summary))
    return summary


def verify_token(token: Optional[str] = None) -> bool:
    """Check if the Oura token is valid."""
    try:
        resp = requests.get(
            "https://api.ouraring.com/v2/usercollection/personal_info",
            headers=_headers(token),
            timeout=10,
        )
        return resp.status_code == 200
    except requests.RequestException:
        return False
