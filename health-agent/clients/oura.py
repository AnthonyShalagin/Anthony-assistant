"""Oura Ring API client — bearer token authentication.

Fetches sleep, readiness, activity, and HRV data.
API docs: https://cloud.ouraring.com/v2/docs
"""

import logging
from datetime import date, timedelta
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

        # Activity
        try:
            activity_data = fetch_activity(target, token)
            if activity_data:
                a = activity_data[0]
                score = a.get("score")
                if score is not None:
                    upsert_metric(conn, target, "oura", "activity_score", score, "score")
                    summary["activity_score"] = score
                for key in ("active_calories", "steps", "equivalent_walking_distance"):
                    val = a.get(key)
                    if val is not None:
                        unit = "kcal" if "calories" in key else ("steps" if key == "steps" else "meters")
                        upsert_metric(conn, target, "oura", key, val, unit)
                        summary[key] = val
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
