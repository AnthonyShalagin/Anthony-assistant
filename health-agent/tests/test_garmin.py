"""Tests for the Garmin API client."""

import json
from unittest.mock import patch, MagicMock

from database import get_db, save_oauth_token
from clients.garmin import _to_epoch


def test_to_epoch_start_of_day():
    """_to_epoch returns midnight UTC for a date."""
    epoch = _to_epoch("2024-03-15")
    # 2024-03-15 00:00:00 UTC
    assert epoch == 1710460800


def test_to_epoch_end_of_day():
    """_to_epoch with end=True returns next day midnight."""
    epoch = _to_epoch("2024-03-15", end=True)
    # 2024-03-16 00:00:00 UTC
    assert epoch == 1710547200


@patch("clients.garmin.OAuth1Session")
def test_pull_daily_stores_metrics(mock_session_cls, tmp_db):
    """pull_daily fetches and stores Garmin metrics."""
    # Store a fake token
    with get_db(tmp_db) as conn:
        save_oauth_token(conn, "garmin", "access123",
                        extra=json.dumps({"resource_owner_secret": "secret456"}))

    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session

    # Daily summary
    daily_resp = MagicMock()
    daily_resp.json.return_value = [{
        "steps": 9500,
        "activeKilocalories": 520,
        "totalKilocalories": 2200,
        "distanceInMeters": 7200,
        "moderateIntensityDurationInSeconds": 1800,
        "vigorousIntensityDurationInSeconds": 600,
    }]
    daily_resp.status_code = 200
    daily_resp.raise_for_status = MagicMock()

    # Body battery
    bb_resp = MagicMock()
    bb_resp.json.return_value = [
        {"bodyBatteryValue": 45},
        {"bodyBatteryValue": 80},
        {"bodyBatteryValue": 30},
    ]
    bb_resp.status_code = 200
    bb_resp.raise_for_status = MagicMock()

    # Stress
    stress_resp = MagicMock()
    stress_resp.json.return_value = [
        {"stressLevel": 25},
        {"stressLevel": 40},
        {"stressLevel": 15},
    ]
    stress_resp.status_code = 200
    stress_resp.raise_for_status = MagicMock()

    mock_session.get.side_effect = [daily_resp, bb_resp, stress_resp]

    from clients.garmin import pull_daily
    summary = pull_daily("2024-03-15", db_path=tmp_db)

    assert "steps" in summary
    assert summary["steps"] == 9500
    assert "body_battery_high" in summary
    assert summary["body_battery_high"] == 80
    assert "body_battery_low" in summary
    assert summary["body_battery_low"] == 30
    assert "avg_stress" in summary


def test_verify_token_no_token(tmp_db):
    """verify_token returns False when no token is stored."""
    from clients.garmin import verify_token
    assert verify_token(tmp_db) is False
