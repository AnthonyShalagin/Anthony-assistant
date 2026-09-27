"""Tests for the Hevy API client. Shapes follow the Hevy OpenAPI spec (api.hevyapp.com/docs)."""

from unittest.mock import MagicMock, patch

import requests

from clients.hevy import _local_day, fetch_workouts, pull_daily, pull_range
from database import get_db


def _workout(start, end, title="Push", sets=None):
    return {
        "id": "w-" + start, "title": title, "start_time": start, "end_time": end,
        "exercises": [{"index": 0, "title": "Bench Press (Barbell)",
                       "sets": sets if sets is not None else [
                           {"index": 0, "type": "warmup", "weight_kg": 20, "reps": 10, "rpe": None},
                           {"index": 1, "type": "normal", "weight_kg": 61.235, "reps": 8, "rpe": 8},
                           {"index": 2, "type": "failure", "weight_kg": 61.235, "reps": 6, "rpe": None},
                           {"index": 3, "type": "normal", "weight_kg": 61.235, "reps": 8, "rpe": 7},
                       ]}],
    }


def _resp(workouts, page=1, page_count=1):
    r = MagicMock()
    r.json.return_value = {"page": page, "page_count": page_count, "workouts": workouts}
    r.raise_for_status = MagicMock()
    return r


def test_local_day_uses_eastern_time():
    # 01:30 UTC on the 21st is 9:30pm on the 20th in New York
    assert _local_day("2026-09-21T01:30:00Z") == "2026-09-20"
    assert _local_day(None) is None


@patch("clients.hevy.requests.get")
def test_pull_range_writes_sessions_sets_and_rest_day_zeros(mock_get, tmp_db):
    mock_get.return_value = _resp([_workout("2026-09-20T14:00:00Z", "2026-09-20T14:45:00Z")])
    result = pull_range("2026-09-19", "2026-09-20", api_key="k", db_path=tmp_db)

    assert result["workouts"] == 1
    assert result["days"]["2026-09-20"] == {"strength_sessions": 1, "strength_minutes": 45.0,
                                            "working_sets": 3, "hard_sets": 2, "rpe_logged_sets": 2}
    assert result["days"]["2026-09-19"]["strength_sessions"] == 0
    with get_db(tmp_db) as conn:
        rows = conn.execute("SELECT * FROM workouts ORDER BY set_order").fetchall()
        rest = conn.execute("SELECT value FROM health_metrics WHERE date='2026-09-19' AND source='hevy' "
                            "AND metric_name='strength_sessions'").fetchone()
    assert len(rows) == 3  # warmup skipped
    assert rows[0]["weight"] == 135.0  # kg converted to lb
    assert rows[0]["reps"] == 8
    assert rest["value"] == 0


@patch("clients.hevy.requests.get")
def test_fetch_stops_paging_once_past_start(mock_get):
    mock_get.side_effect = [
        _resp([_workout("2026-09-25T14:00:00Z", "2026-09-25T15:00:00Z"),
               _workout("2026-09-10T14:00:00Z", "2026-09-10T15:00:00Z")], page=1, page_count=9),
    ]
    out = fetch_workouts("2026-09-20", api_key="k")
    assert [w["start_time"][:10] for w in out] == ["2026-09-25"]
    assert mock_get.call_count == 1


@patch("clients.hevy.requests.get")
def test_pull_daily_returns_error_instead_of_raising(mock_get, tmp_db):
    mock_get.side_effect = requests.ConnectionError("down")
    assert "error" in pull_daily("2026-09-20", api_key="k", db_path=tmp_db)


@patch("clients.hevy.requests.get")
def test_real_response_quirks(mock_get, tmp_db):
    """Shapes seen in the live API (Sept 27 2026): '+00:00' timestamps, a duration-only
    'Warm Up', bodyweight sets with no weight, and a carry with no reps."""
    w = {"id": "x", "title": "Full Body", "start_time": "2026-09-27T15:01:55+00:00",
         "end_time": "2026-09-27T15:40:36+00:00", "exercises": [
             {"title": "Warm Up", "sets": [{"type": "normal", "weight_kg": None, "reps": None,
                                            "duration_seconds": 2317, "rpe": None}]},
             {"title": "Push Up", "sets": [{"type": "warmup", "weight_kg": None, "reps": 5, "rpe": None},
                                           {"type": "normal", "weight_kg": None, "reps": 8, "rpe": None}]},
             {"title": "Farmers Walk", "sets": [{"type": "normal", "weight_kg": 18.14, "reps": None, "rpe": None}]},
         ]}
    mock_get.return_value = _resp([w])
    day = pull_range("2026-09-27", "2026-09-27", api_key="k", db_path=tmp_db)["days"]["2026-09-27"]
    assert day["strength_sessions"] == 1
    assert day["strength_minutes"] == 38.7
    assert day["working_sets"] == 2
