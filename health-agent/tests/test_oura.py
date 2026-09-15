"""Tests for the Oura API client."""

from unittest.mock import patch, MagicMock

from clients.oura import pull_daily, verify_token, fetch_sleep


def _mock_oura_responses():
    """Create mock responses for all Oura endpoints."""
    sleep_resp = MagicMock()
    sleep_resp.json.return_value = {
        "data": [{
            "score": 82,
            "contributors": {
                "efficiency": 90,
                "latency": 85,
                "restfulness": 78,
            },
            "total_sleep_duration": 28800,
        }]
    }
    sleep_resp.status_code = 200
    sleep_resp.raise_for_status = MagicMock()

    readiness_resp = MagicMock()
    readiness_resp.json.return_value = {
        "data": [{
            "score": 75,
            "contributors": {
                "activity_balance": 80,
                "body_temperature": 90,
                "hrv_balance": 70,
                "recovery_index": 85,
                "resting_heart_rate": 88,
                "sleep_balance": 72,
            },
        }]
    }
    readiness_resp.status_code = 200
    readiness_resp.raise_for_status = MagicMock()

    activity_resp = MagicMock()
    activity_resp.json.return_value = {
        "data": [{
            "score": 88,
            "active_calories": 450,
            "steps": 8500,
            "equivalent_walking_distance": 6200,
        }]
    }
    activity_resp.status_code = 200
    activity_resp.raise_for_status = MagicMock()

    hrv_resp = MagicMock()
    hrv_resp.json.return_value = {
        "data": [{
            "breath_average": 15.5,
            "heart_rate_average": 58,
            "hrv_average": 42,
            "temperature_deviation": 0.1,
        }]
    }
    hrv_resp.status_code = 200
    hrv_resp.raise_for_status = MagicMock()

    workout_resp = MagicMock()
    workout_resp.json.return_value = {
        "data": [
            {   # Strong session imported through Apple Health
                "activity": "strength_training",
                "day": "2024-03-14",
                "start_datetime": "2024-03-14T18:00:00-04:00",
                "end_datetime": "2024-03-14T18:50:00-04:00",
            },
            {
                "activity": "walking",
                "day": "2024-03-15",
                "start_datetime": "2024-03-15T07:00:00-04:00",
                "end_datetime": "2024-03-15T07:30:00-04:00",
            },
        ]
    }
    workout_resp.status_code = 200
    workout_resp.raise_for_status = MagicMock()

    return [sleep_resp, readiness_resp, activity_resp, hrv_resp, workout_resp]


@patch("clients.oura.requests.get")
def test_pull_daily_stores_metrics(mock_get, tmp_db):
    """pull_daily fetches from all endpoints and stores in DB."""
    mock_get.side_effect = _mock_oura_responses()

    summary = pull_daily("2024-03-15", token="fake-token", db_path=tmp_db)

    assert "sleep_score" in summary
    assert summary["sleep_score"] == 82
    assert "readiness_score" in summary
    assert "activity_score" in summary
    assert "hrv_average" in summary


@patch("clients.oura.requests.get")
def test_pull_daily_counts_strength_workouts(mock_get, tmp_db):
    """Workouts for yesterday and today are stored per day, zeros included."""
    from database import get_db

    mock_get.side_effect = _mock_oura_responses()
    summary = pull_daily("2024-03-15", token="fake-token", db_path=tmp_db)

    assert summary["workouts"]["2024-03-14"]["strength_sessions"] == 1
    assert summary["workouts"]["2024-03-14"]["strength_minutes"] == 50.0
    assert summary["workouts"]["2024-03-15"]["strength_sessions"] == 0
    assert summary["workouts"]["2024-03-15"]["workout_count"] == 1

    with get_db(tmp_db) as conn:
        row = conn.execute(
            "SELECT value FROM health_metrics WHERE date='2024-03-15' "
            "AND source='oura' AND metric_name='strength_sessions'"
        ).fetchone()
    assert row["value"] == 0


@patch("clients.oura.requests.get")
def test_pull_daily_repulls_yesterdays_full_activity(mock_get, tmp_db):
    """Yesterday's finished steps overwrite the partial morning snapshot."""
    from database import get_db, upsert_metric

    with get_db(tmp_db) as conn:  # what the previous morning's pull stored
        upsert_metric(conn, "2024-03-14", "oura", "steps", 210, "steps")

    responses = _mock_oura_responses()
    responses[2].json.return_value = {"data": [
        {"day": "2024-03-14", "score": 85, "steps": 9400, "active_calories": 510},
        {"day": "2024-03-15", "score": 88, "steps": 240, "active_calories": 20},
    ]}
    mock_get.side_effect = responses

    summary = pull_daily("2024-03-15", token="fake-token", db_path=tmp_db)

    assert summary["steps"] == 240  # summary still describes the target day
    with get_db(tmp_db) as conn:
        row = conn.execute(
            "SELECT value FROM health_metrics WHERE date='2024-03-14' "
            "AND source='oura' AND metric_name='steps'"
        ).fetchone()
    assert row["value"] == 9400


@patch("clients.oura.requests.get")
def test_pull_daily_handles_api_error(mock_get, tmp_db):
    """pull_daily handles API errors gracefully."""
    import requests
    mock_get.side_effect = requests.RequestException("API down")

    summary = pull_daily("2024-03-15", token="fake-token", db_path=tmp_db)

    assert "sleep_error" in summary


@patch("clients.oura.requests.get")
def test_verify_token_valid(mock_get):
    """verify_token returns True for 200 response."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_get.return_value = mock_resp

    assert verify_token("valid-token") is True


@patch("clients.oura.requests.get")
def test_verify_token_invalid(mock_get):
    """verify_token returns False for non-200 response."""
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_get.return_value = mock_resp

    assert verify_token("bad-token") is False
