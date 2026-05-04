"""Shared test fixtures."""

import os
import sys
import tempfile

import pytest

# Add parent directory to path so tests can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def tmp_db(tmp_path):
    """Create a temporary SQLite database."""
    db_path = str(tmp_path / "test.db")
    from database import init_db
    init_db(db_path)
    return db_path


@pytest.fixture
def populated_db(tmp_db):
    """Create a DB pre-populated with sample health metrics."""
    from datetime import date, timedelta
    from database import get_db, upsert_metric, upsert_workout

    with get_db(tmp_db) as conn:
        # Add 14 days of sample metrics for trend testing
        today = date.today()
        for i in range(14):
            dt = (today - timedelta(days=i)).isoformat()

            # Oura metrics
            upsert_metric(conn, dt, "oura", "sleep_score", 75 + i % 10, "score")
            upsert_metric(conn, dt, "oura", "readiness_score", 70 + i % 15, "score")
            upsert_metric(conn, dt, "oura", "activity_score", 65 + i % 20, "score")
            upsert_metric(conn, dt, "oura", "hrv_average", 40 + i % 12, "ms")

            # Whoop metrics
            upsert_metric(conn, dt, "whoop", "recovery_score", 60 + i % 20, "%")
            upsert_metric(conn, dt, "whoop", "strain_score", 8 + (i % 8), "score")
            upsert_metric(conn, dt, "whoop", "hrv_rmssd", 45 + i % 15, "ms")
            upsert_metric(conn, dt, "whoop", "sleep_performance", 70 + i % 15, "%")

        # Add sample workouts
        for day_offset in [0, 2, 4]:
            dt = (today - timedelta(days=day_offset)).isoformat()
            for set_num in range(1, 4):
                upsert_workout(conn, dt, "Push Day", "Bench Press", set_num,
                              100.0, 8, 800.0, 126.7)
                upsert_workout(conn, dt, "Push Day", "Overhead Press", set_num,
                              60.0, 10, 600.0, 80.0)

    return tmp_db


@pytest.fixture
def sample_strong_csv():
    """Return sample Strong app CSV content."""
    return (
        "Date,Workout Name,Exercise Name,Set Order,Weight,Reps,Distance,Seconds,Notes,Workout Notes,RPE\n"
        "2024-03-15 10:00:00,Push Day,Bench Press,1,100,8,0,0,,, \n"
        "2024-03-15 10:00:00,Push Day,Bench Press,2,100,8,0,0,,, \n"
        "2024-03-15 10:00:00,Push Day,Bench Press,3,110,5,0,0,,, \n"
        "2024-03-15 10:00:00,Push Day,Overhead Press,1,60,10,0,0,,, \n"
        "2024-03-15 10:00:00,Push Day,Overhead Press,2,60,8,0,0,,, \n"
        "2024-03-15 10:00:00,Push Day,Overhead Press,3,65,6,0,0,,, \n"
        "2024-03-17 09:00:00,Pull Day,Deadlift,1,140,5,0,0,,, \n"
        "2024-03-17 09:00:00,Pull Day,Deadlift,2,140,5,0,0,,, \n"
        "2024-03-17 09:00:00,Pull Day,Barbell Row,1,80,8,0,0,,, \n"
        "2024-03-17 09:00:00,Pull Day,Barbell Row,2,80,8,0,0,,, \n"
    )
