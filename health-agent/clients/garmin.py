"""Garmin Connect API client — OAuth 1.0a authentication.

Fetches steps, body battery, stress, and intensity minutes.
Uses the Garmin Connect wellness API endpoints.
"""

import json
import logging
from datetime import date, timedelta
from typing import Optional

import requests
from requests_oauthlib import OAuth1Session

from config import GARMIN_CONSUMER_KEY, GARMIN_CONSUMER_SECRET
from database import get_db, load_oauth_token, save_oauth_token, upsert_metric

logger = logging.getLogger(__name__)

REQUEST_TOKEN_URL = "https://connectapi.garmin.com/oauth-service/oauth/request_token"
AUTHORIZE_URL = "https://connect.garmin.com/oauthConfirm"
ACCESS_TOKEN_URL = "https://connectapi.garmin.com/oauth-service/oauth/access_token"
BASE_URL = "https://apis.garmin.com/wellness-api/rest"


def _get_session(db_path: Optional[str] = None) -> Optional[OAuth1Session]:
    """Create an OAuth 1.0a session with stored tokens."""
    db_kwargs = {"db_path": db_path} if db_path else {}
    with get_db(**db_kwargs) as conn:
        token_data = load_oauth_token(conn, "garmin")

    if not token_data:
        logger.warning("No Garmin OAuth token found in database")
        return None

    extra = {}
    if token_data.get("extra"):
        try:
            extra = json.loads(token_data["extra"])
        except (json.JSONDecodeError, TypeError):
            pass

    session = OAuth1Session(
        client_key=GARMIN_CONSUMER_KEY,
        client_secret=GARMIN_CONSUMER_SECRET,
        resource_owner_key=token_data["access_token"],
        resource_owner_secret=extra.get("resource_owner_secret", ""),
    )
    return session


def _get(endpoint: str, params: dict = None, db_path: Optional[str] = None) -> dict:
    """Make an authenticated GET to the Garmin API."""
    session = _get_session(db_path)
    if not session:
        raise RuntimeError("Garmin OAuth session not available — run initial auth first")
    resp = session.get(f"{BASE_URL}/{endpoint}", params=params or {}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_daily_summary(dt: Optional[str] = None, db_path: Optional[str] = None) -> list[dict]:
    """Fetch daily summary (steps, distance, calories)."""
    target = dt or date.today().isoformat()
    data = _get("dailies", {"uploadStartTimeInSeconds": _to_epoch(target),
                            "uploadEndTimeInSeconds": _to_epoch(target, end=True)}, db_path)
    return data if isinstance(data, list) else []


def fetch_body_battery(dt: Optional[str] = None, db_path: Optional[str] = None) -> list[dict]:
    """Fetch body battery data."""
    target = dt or date.today().isoformat()
    data = _get("bodyBattery", {"startTimeInSeconds": _to_epoch(target),
                                "endTimeInSeconds": _to_epoch(target, end=True)}, db_path)
    return data if isinstance(data, list) else []


def fetch_stress(dt: Optional[str] = None, db_path: Optional[str] = None) -> list[dict]:
    """Fetch stress data."""
    target = dt or date.today().isoformat()
    data = _get("stressDetails", {"startTimeInSeconds": _to_epoch(target),
                                  "endTimeInSeconds": _to_epoch(target, end=True)}, db_path)
    return data if isinstance(data, list) else []


def _to_epoch(dt_str: str, end: bool = False) -> int:
    """Convert date string to epoch seconds (start or end of day)."""
    from datetime import datetime, timezone
    d = date.fromisoformat(dt_str)
    if end:
        d = d + timedelta(days=1)
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())


def pull_daily(dt: Optional[str] = None, db_path: Optional[str] = None) -> dict:
    """Pull all Garmin metrics for a date and store in DB."""
    target = dt or date.today().isoformat()
    summary = {}
    db_kwargs = {"db_path": db_path} if db_path else {}

    with get_db(**db_kwargs) as conn:
        # Daily summary (steps, active calories, intensity minutes)
        try:
            daily_data = fetch_daily_summary(target, db_path)
            if daily_data:
                d = daily_data[0]
                metrics = {
                    "steps": (d.get("steps"), "steps"),
                    "active_calories": (d.get("activeKilocalories"), "kcal"),
                    "total_calories": (d.get("totalKilocalories"), "kcal"),
                    "distance": (d.get("distanceInMeters"), "meters"),
                    "moderate_intensity_minutes": (d.get("moderateIntensityDurationInSeconds", 0) // 60 if d.get("moderateIntensityDurationInSeconds") else None, "min"),
                    "vigorous_intensity_minutes": (d.get("vigorousIntensityDurationInSeconds", 0) // 60 if d.get("vigorousIntensityDurationInSeconds") else None, "min"),
                }
                for name, (value, unit) in metrics.items():
                    if value is not None:
                        upsert_metric(conn, target, "garmin", name, float(value), unit)
                        summary[name] = value
        except Exception as e:
            logger.error("Garmin daily summary fetch failed: %s", e)
            summary["daily_error"] = str(e)

        # Body battery
        try:
            bb_data = fetch_body_battery(target, db_path)
            if bb_data:
                # Get the highest and lowest body battery of the day
                values = [
                    entry.get("chargedValue", entry.get("bodyBatteryValue", 0))
                    for entry in bb_data
                    if isinstance(entry, dict)
                ]
                if values:
                    upsert_metric(conn, target, "garmin", "body_battery_high", float(max(values)), "level")
                    upsert_metric(conn, target, "garmin", "body_battery_low", float(min(values)), "level")
                    summary["body_battery_high"] = max(values)
                    summary["body_battery_low"] = min(values)
        except Exception as e:
            logger.error("Garmin body battery fetch failed: %s", e)
            summary["body_battery_error"] = str(e)

        # Stress
        try:
            stress_data = fetch_stress(target, db_path)
            if stress_data:
                stress_values = [
                    entry.get("stressLevel", 0)
                    for entry in stress_data
                    if isinstance(entry, dict) and entry.get("stressLevel", -1) >= 0
                ]
                if stress_values:
                    avg_stress = sum(stress_values) / len(stress_values)
                    upsert_metric(conn, target, "garmin", "avg_stress", round(avg_stress, 1), "level")
                    upsert_metric(conn, target, "garmin", "max_stress", float(max(stress_values)), "level")
                    summary["avg_stress"] = round(avg_stress, 1)
                    summary["max_stress"] = max(stress_values)
        except Exception as e:
            logger.error("Garmin stress fetch failed: %s", e)
            summary["stress_error"] = str(e)

    logger.info("Garmin pull complete for %s: %d metrics", target, len(summary))
    return summary


def verify_token(db_path: Optional[str] = None) -> bool:
    """Check if the stored Garmin token is valid."""
    try:
        session = _get_session(db_path)
        if not session:
            return False
        resp = session.get(f"{BASE_URL}/userMetrics", timeout=10)
        return resp.status_code == 200
    except Exception:
        return False


def initiate_auth() -> tuple[str, dict]:
    """Start OAuth 1.0a flow — returns (authorize_url, request_token_data)."""
    session = OAuth1Session(
        client_key=GARMIN_CONSUMER_KEY,
        client_secret=GARMIN_CONSUMER_SECRET,
    )
    tokens = session.fetch_request_token(REQUEST_TOKEN_URL)
    auth_url = session.authorization_url(AUTHORIZE_URL)
    return auth_url, tokens


def complete_auth(
    verifier: str,
    request_token: str,
    request_token_secret: str,
    db_path: Optional[str] = None,
) -> dict:
    """Complete OAuth 1.0a flow with the verifier and store tokens."""
    session = OAuth1Session(
        client_key=GARMIN_CONSUMER_KEY,
        client_secret=GARMIN_CONSUMER_SECRET,
        resource_owner_key=request_token,
        resource_owner_secret=request_token_secret,
    )
    tokens = session.fetch_access_token(ACCESS_TOKEN_URL, verifier=verifier)
    db_kwargs = {"db_path": db_path} if db_path else {}
    with get_db(**db_kwargs) as conn:
        save_oauth_token(
            conn,
            "garmin",
            tokens["oauth_token"],
            extra=json.dumps({"resource_owner_secret": tokens["oauth_token_secret"]}),
        )
    return tokens
