"""Tests for the SQLite database layer."""

from datetime import date, timedelta

from database import (
    get_db, init_db, upsert_metric, upsert_workout,
    save_oauth_token, load_oauth_token, get_metrics,
    get_metric_average, get_recent_workouts,
)


def test_init_creates_tables(tmp_db):
    """init_db creates all three required tables."""
    with get_db(tmp_db) as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {r["name"] for r in tables}
    assert "health_metrics" in table_names
    assert "workouts" in table_names
    assert "oauth_tokens" in table_names


def test_upsert_metric_insert(tmp_db):
    """upsert_metric inserts a new metric."""
    with get_db(tmp_db) as conn:
        upsert_metric(conn, "2024-03-15", "oura", "sleep_score", 85, "score")
        rows = conn.execute("SELECT * FROM health_metrics").fetchall()
    assert len(rows) == 1
    assert rows[0]["value"] == 85


def test_upsert_metric_update(tmp_db):
    """upsert_metric updates on conflict (same date+source+metric_name)."""
    with get_db(tmp_db) as conn:
        upsert_metric(conn, "2024-03-15", "oura", "sleep_score", 85, "score")
        upsert_metric(conn, "2024-03-15", "oura", "sleep_score", 90, "score")
        rows = conn.execute("SELECT * FROM health_metrics").fetchall()
    assert len(rows) == 1
    assert rows[0]["value"] == 90


def test_upsert_workout_insert(tmp_db):
    """upsert_workout inserts a new workout set."""
    with get_db(tmp_db) as conn:
        upsert_workout(conn, "2024-03-15", "Push Day", "Bench Press", 1,
                       100.0, 8, 800.0, 126.7)
        rows = conn.execute("SELECT * FROM workouts").fetchall()
    assert len(rows) == 1
    assert rows[0]["exercise"] == "Bench Press"
    assert rows[0]["volume"] == 800.0


def test_upsert_workout_update(tmp_db):
    """upsert_workout updates on conflict."""
    with get_db(tmp_db) as conn:
        upsert_workout(conn, "2024-03-15", "Push Day", "Bench Press", 1,
                       100.0, 8, 800.0, 126.7)
        upsert_workout(conn, "2024-03-15", "Push Day", "Bench Press", 1,
                       105.0, 6, 630.0, 126.0)
        rows = conn.execute("SELECT * FROM workouts").fetchall()
    assert len(rows) == 1
    assert rows[0]["weight"] == 105.0


def test_oauth_token_save_and_load(tmp_db):
    """save_oauth_token stores token; load_oauth_token retrieves it."""
    with get_db(tmp_db) as conn:
        save_oauth_token(conn, "whoop", "access123", "refresh456", "Bearer",
                        "2025-01-01T00:00:00")
        token = load_oauth_token(conn, "whoop")
    assert token is not None
    assert token["access_token"] == "access123"
    assert token["refresh_token"] == "refresh456"


def test_oauth_token_upsert_preserves_refresh(tmp_db):
    """Updating an OAuth token preserves the refresh token if new one is None."""
    with get_db(tmp_db) as conn:
        save_oauth_token(conn, "whoop", "old_access", "refresh456")
        save_oauth_token(conn, "whoop", "new_access", None)
        token = load_oauth_token(conn, "whoop")
    assert token["access_token"] == "new_access"
    assert token["refresh_token"] == "refresh456"


def test_load_missing_oauth_token(tmp_db):
    """load_oauth_token returns None for unknown provider."""
    with get_db(tmp_db) as conn:
        token = load_oauth_token(conn, "nonexistent")
    assert token is None


def test_get_metrics_filters_by_source(populated_db):
    """get_metrics filters by source."""
    with get_db(populated_db) as conn:
        oura = get_metrics(conn, source="oura", days=7)
        whoop = get_metrics(conn, source="whoop", days=7)
    assert all(m["source"] == "oura" for m in oura)
    assert all(m["source"] == "whoop" for m in whoop)


def test_get_metric_average(populated_db):
    """get_metric_average returns a float for populated data."""
    with get_db(populated_db) as conn:
        avg = get_metric_average(conn, "oura", "sleep_score", days=7)
    assert avg is not None
    assert isinstance(avg, float)
    assert 70 <= avg <= 90


def test_get_metric_average_missing(tmp_db):
    """get_metric_average returns None when no data exists."""
    with get_db(tmp_db) as conn:
        avg = get_metric_average(conn, "oura", "sleep_score", days=7)
    assert avg is None


def test_get_recent_workouts(populated_db):
    """get_recent_workouts returns workout data."""
    with get_db(populated_db) as conn:
        workouts = get_recent_workouts(conn, days=7)
    assert len(workouts) > 0
    assert "exercise" in workouts[0]
