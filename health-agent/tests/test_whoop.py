"""Tests for the Whoop API client."""

from unittest.mock import patch, MagicMock

from database import get_db, save_oauth_token


@patch("clients.whoop.OAuth2Session")
def test_pull_daily_stores_metrics(mock_session_cls, tmp_db):
    """pull_daily fetches recovery, strain, and sleep data."""
    # Set up stored token
    with get_db(tmp_db) as conn:
        save_oauth_token(conn, "whoop", "access123", "refresh456",
                        expires_at="2030-01-01T00:00:00+00:00")

    # Mock the OAuth2Session instance
    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session

    # Recovery response
    recovery_resp = MagicMock()
    recovery_resp.json.return_value = {
        "records": [{
            "score": {
                "recovery_score": 75,
                "resting_heart_rate": 55,
                "hrv_rmssd_milli": 48.5,
                "spo2_percentage": 97.0,
                "skin_temp_celsius": 33.2,
            }
        }]
    }
    recovery_resp.status_code = 200
    recovery_resp.raise_for_status = MagicMock()

    # Strain response
    strain_resp = MagicMock()
    strain_resp.json.return_value = {
        "records": [{
            "score": {
                "strain": 12.5,
                "kilojoule": 2100,
                "average_heart_rate": 72,
            }
        }]
    }
    strain_resp.status_code = 200
    strain_resp.raise_for_status = MagicMock()

    # Sleep response
    sleep_resp = MagicMock()
    sleep_resp.json.return_value = {
        "records": [{
            "score": {
                "sleep_performance_percentage": 85,
                "sleep_consistency_percentage": 80,
                "sleep_efficiency_percentage": 92,
            }
        }]
    }
    sleep_resp.status_code = 200
    sleep_resp.raise_for_status = MagicMock()

    mock_session.get.side_effect = [recovery_resp, strain_resp, sleep_resp]

    from clients.whoop import pull_daily
    summary = pull_daily("2024-03-15", db_path=tmp_db)

    assert "recovery_score" in summary
    assert summary["recovery_score"] == 75
    assert "strain_score" in summary
    assert "sleep_performance" in summary


def test_verify_token_no_token(tmp_db):
    """verify_token returns False when no token is stored."""
    from clients.whoop import verify_token
    assert verify_token(tmp_db) is False
