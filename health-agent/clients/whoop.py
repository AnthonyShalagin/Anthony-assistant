"""Whoop API client — OAuth2 with automatic token refresh.

Fetches strain, recovery, HRV, and sleep performance.
API docs: https://developer.whoop.com/api
"""

import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import requests
from requests_oauthlib import OAuth2Session

from config import WHOOP_CLIENT_ID, WHOOP_CLIENT_SECRET, WHOOP_REDIRECT_URI
from database import get_db, load_oauth_token, save_oauth_token, upsert_metric

logger = logging.getLogger(__name__)

TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
BASE_URL = "https://api.prod.whoop.com/developer/v1"
AUTHORIZE_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"


def _get_session(db_path: Optional[str] = None) -> Optional[OAuth2Session]:
    """Create an OAuth2 session with stored tokens, auto-refreshing if needed."""
    db_kwargs = {"db_path": db_path} if db_path else {}
    with get_db(**db_kwargs) as conn:
        token_data = load_oauth_token(conn, "whoop")

    if not token_data:
        logger.warning("No Whoop OAuth token found in database")
        return None

    token = {
        "access_token": token_data["access_token"],
        "refresh_token": token_data.get("refresh_token", ""),
        "token_type": token_data.get("token_type", "Bearer"),
    }
    if token_data.get("expires_at"):
        token["expires_at"] = float(
            datetime.fromisoformat(token_data["expires_at"]).timestamp()
        )

    def _save_refreshed(new_token, *args, **kwargs):
        with get_db(**db_kwargs) as conn:
            expires = None
            if "expires_at" in new_token:
                expires = datetime.fromtimestamp(
                    new_token["expires_at"], tz=timezone.utc
                ).isoformat()
            save_oauth_token(
                conn,
                "whoop",
                new_token["access_token"],
                new_token.get("refresh_token"),
                new_token.get("token_type", "Bearer"),
                expires,
            )
        logger.info("Whoop token refreshed and saved")

    session = OAuth2Session(
        client_id=WHOOP_CLIENT_ID,
        token=token,
        auto_refresh_url=TOKEN_URL,
        auto_refresh_kwargs={
            "client_id": WHOOP_CLIENT_ID,
            "client_secret": WHOOP_CLIENT_SECRET,
        },
        token_updater=_save_refreshed,
    )
    return session


def _get(endpoint: str, params: dict = None, db_path: Optional[str] = None) -> dict:
    """Make an authenticated GET to the Whoop API."""
    session = _get_session(db_path)
    if not session:
        raise RuntimeError("Whoop OAuth session not available — run initial auth first")
    resp = session.get(f"{BASE_URL}/{endpoint}", params=params or {}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_recovery(dt: Optional[str] = None, db_path: Optional[str] = None) -> list[dict]:
    """Fetch recovery data for a date range."""
    target = dt or date.today().isoformat()
    next_day = (date.fromisoformat(target) + timedelta(days=1)).isoformat()
    data = _get(
        "recovery",
        {"start": f"{target}T00:00:00.000Z", "end": f"{next_day}T00:00:00.000Z"},
        db_path,
    )
    return data.get("records", [])


def fetch_strain(dt: Optional[str] = None, db_path: Optional[str] = None) -> list[dict]:
    """Fetch strain (cycle) data for a date range."""
    target = dt or date.today().isoformat()
    next_day = (date.fromisoformat(target) + timedelta(days=1)).isoformat()
    data = _get(
        "cycle",
        {"start": f"{target}T00:00:00.000Z", "end": f"{next_day}T00:00:00.000Z"},
        db_path,
    )
    return data.get("records", [])


def fetch_sleep(dt: Optional[str] = None, db_path: Optional[str] = None) -> list[dict]:
    """Fetch sleep data for a date range."""
    target = dt or date.today().isoformat()
    next_day = (date.fromisoformat(target) + timedelta(days=1)).isoformat()
    data = _get(
        "activity/sleep",
        {"start": f"{target}T00:00:00.000Z", "end": f"{next_day}T00:00:00.000Z"},
        db_path,
    )
    return data.get("records", [])


def pull_daily(dt: Optional[str] = None, db_path: Optional[str] = None) -> dict:
    """Pull all Whoop metrics for a date and store in DB."""
    target = dt or date.today().isoformat()
    summary = {}
    db_kwargs = {"db_path": db_path} if db_path else {}

    with get_db(**db_kwargs) as conn:
        # Recovery
        try:
            recovery_data = fetch_recovery(target, db_path)
            if recovery_data:
                r = recovery_data[0]
                score = r.get("score", {})
                metrics = {
                    "recovery_score": score.get("recovery_score"),
                    "resting_heart_rate": score.get("resting_heart_rate"),
                    "hrv_rmssd": score.get("hrv_rmssd_milli"),
                    "spo2": score.get("spo2_percentage"),
                    "skin_temp": score.get("skin_temp_celsius"),
                }
                for name, value in metrics.items():
                    if value is not None:
                        unit = {
                            "recovery_score": "%",
                            "resting_heart_rate": "bpm",
                            "hrv_rmssd": "ms",
                            "spo2": "%",
                            "skin_temp": "°C",
                        }.get(name, "")
                        upsert_metric(conn, target, "whoop", name, value, unit)
                        summary[name] = value
        except Exception as e:
            logger.error("Whoop recovery fetch failed: %s", e)
            summary["recovery_error"] = str(e)

        # Strain
        try:
            strain_data = fetch_strain(target, db_path)
            if strain_data:
                s = strain_data[0]
                score = s.get("score", {})
                strain = score.get("strain")
                if strain is not None:
                    upsert_metric(conn, target, "whoop", "strain_score", strain, "score")
                    summary["strain_score"] = strain
                kilojoule = score.get("kilojoule")
                if kilojoule is not None:
                    upsert_metric(conn, target, "whoop", "kilojoules", kilojoule, "kJ")
                    summary["kilojoules"] = kilojoule
                avg_hr = score.get("average_heart_rate")
                if avg_hr is not None:
                    upsert_metric(conn, target, "whoop", "avg_heart_rate", avg_hr, "bpm")
                    summary["avg_heart_rate"] = avg_hr
        except Exception as e:
            logger.error("Whoop strain fetch failed: %s", e)
            summary["strain_error"] = str(e)

        # Sleep
        try:
            sleep_data = fetch_sleep(target, db_path)
            if sleep_data:
                s = sleep_data[0]
                score = s.get("score", {})
                metrics = {
                    "sleep_performance": score.get("sleep_performance_percentage"),
                    "sleep_consistency": score.get("sleep_consistency_percentage"),
                    "sleep_efficiency": score.get("sleep_efficiency_percentage"),
                }
                for name, value in metrics.items():
                    if value is not None:
                        upsert_metric(conn, target, "whoop", name, value, "%")
                        summary[name] = value
        except Exception as e:
            logger.error("Whoop sleep fetch failed: %s", e)
            summary["sleep_error"] = str(e)

    logger.info("Whoop pull complete for %s: %d metrics", target, len(summary))
    return summary


def verify_token(db_path: Optional[str] = None) -> bool:
    """Check if the stored Whoop token is valid (or can be refreshed)."""
    try:
        session = _get_session(db_path)
        if not session:
            return False
        resp = session.get(f"{BASE_URL}/user/profile/basic", timeout=10)
        return resp.status_code == 200
    except Exception:
        return False


def get_auth_url() -> str:
    """Generate the OAuth2 authorization URL for initial setup."""
    session = OAuth2Session(
        WHOOP_CLIENT_ID,
        redirect_uri=WHOOP_REDIRECT_URI,
        scope=["read:recovery", "read:cycles", "read:sleep", "read:profile"],
    )
    url, _ = session.authorization_url(AUTHORIZE_URL)
    return url


def complete_auth(authorization_response: str, db_path: Optional[str] = None) -> dict:
    """Exchange the authorization code for tokens and store them."""
    session = OAuth2Session(
        WHOOP_CLIENT_ID, redirect_uri=WHOOP_REDIRECT_URI
    )
    token = session.fetch_token(
        TOKEN_URL,
        authorization_response=authorization_response,
        client_id=WHOOP_CLIENT_ID,
        client_secret=WHOOP_CLIENT_SECRET,
        include_client_id=True,
    )
    db_kwargs = {"db_path": db_path} if db_path else {}
    with get_db(**db_kwargs) as conn:
        expires = None
        if "expires_at" in token:
            expires = datetime.fromtimestamp(
                token["expires_at"], tz=timezone.utc
            ).isoformat()
        save_oauth_token(
            conn,
            "whoop",
            token["access_token"],
            token.get("refresh_token"),
            token.get("token_type", "Bearer"),
            expires,
        )
    return token
