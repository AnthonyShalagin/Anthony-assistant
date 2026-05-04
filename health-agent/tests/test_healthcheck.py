"""Tests for the healthcheck module."""

from unittest.mock import patch, MagicMock

from healthcheck import check_database, run_healthcheck


def test_check_database_ok(tmp_db):
    """check_database passes on a valid DB."""
    ok, msg = check_database(tmp_db)
    assert ok is True
    assert msg == "OK"


def test_check_database_bad_path():
    """check_database handles unreachable DB path."""
    ok, msg = check_database("/nonexistent/path/db.sqlite")
    assert ok is False


@patch("healthcheck.check_whoop_token", return_value=(True, "OK"))
@patch("healthcheck.check_oura_token", return_value=(True, "OK"))
@patch("healthcheck.send_message")
def test_run_healthcheck_all_ok(mock_send, mock_oura, mock_whoop, tmp_db):
    """run_healthcheck reports all OK."""
    results = run_healthcheck(db_path=tmp_db, notify=True)
    assert all(r["ok"] for r in results.values())
    mock_send.assert_called_once()
    assert "✅" in mock_send.call_args[0][0]


@patch("healthcheck.check_whoop_token", return_value=(False, "Token invalid"))
@patch("healthcheck.check_oura_token", return_value=(True, "OK"))
@patch("healthcheck.send_message")
def test_run_healthcheck_partial_failure(mock_send, mock_oura, mock_whoop, tmp_db):
    """run_healthcheck reports issues when a check fails."""
    results = run_healthcheck(db_path=tmp_db, notify=True)
    assert results["whoop"]["ok"] is False
    assert "⚠️" in mock_send.call_args[0][0]
