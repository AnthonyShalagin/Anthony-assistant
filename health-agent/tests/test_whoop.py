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


@patch("clients.whoop.requests.post")
def test_expired_token_refreshes_with_offline_scope(mock_post, tmp_db):
    """An expiring token is refreshed once, and the rotated refresh token is saved."""
    from database import load_oauth_token
    from clients.whoop import _get_session

    with get_db(tmp_db) as conn:
        save_oauth_token(conn, "whoop", "old-access", "old-refresh",
                         expires_at="2020-01-01T00:00:00+00:00")

    resp = MagicMock()
    resp.json.return_value = {"access_token": "new-access", "refresh_token": "new-refresh",
                              "expires_in": 3600, "token_type": "bearer"}
    resp.raise_for_status = MagicMock()
    mock_post.return_value = resp

    session = _get_session(tmp_db)

    assert session is not None
    sent = mock_post.call_args.kwargs["data"]
    assert sent["refresh_token"] == "old-refresh"
    assert sent["scope"] == "offline"
    with get_db(tmp_db) as conn:
        stored = load_oauth_token(conn, "whoop")
    assert stored["access_token"] == "new-access"
    assert stored["refresh_token"] == "new-refresh"


@patch("clients.whoop.requests.post")
def test_fresh_token_does_not_refresh(mock_post, tmp_db):
    """A token that isn't close to expiry is used as-is."""
    from clients.whoop import _get_session

    with get_db(tmp_db) as conn:
        save_oauth_token(conn, "whoop", "access", "refresh",
                         expires_at="2099-01-01T00:00:00+00:00")

    assert _get_session(tmp_db) is not None
    mock_post.assert_not_called()


def test_verify_token_no_token(tmp_db):
    """verify_token returns False when no token is stored."""
    from clients.whoop import verify_token
    assert verify_token(tmp_db) is False
