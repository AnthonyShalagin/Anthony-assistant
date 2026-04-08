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

    return [sleep_resp, readiness_resp, activity_resp, hrv_resp]


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
