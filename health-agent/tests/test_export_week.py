"""Tests for export_week.py, the Life OS weekly health export."""

from datetime import date

from database import get_db, upsert_metric
from export_week import export


def test_export_groups_metrics_and_skips_garmin(tmp_db):
    with get_db(tmp_db) as conn:
        upsert_metric(conn, "2024-03-14", "oura", "sleep_score", 80, "score")
        upsert_metric(conn, "2024-03-15", "whoop", "recovery_score", 66, "%")
        upsert_metric(conn, "2024-03-15", "garmin", "steps", 9000, "steps")
        upsert_metric(conn, "2024-02-01", "oura", "sleep_score", 70, "score")  # outside window

    out = export(tmp_db, days=14, today=date(2024, 3, 16))

    assert out["metrics_by_date"]["2024-03-14"]["oura"]["sleep_score"] == 80
    assert out["metrics_by_date"]["2024-03-15"]["whoop"]["recovery_score"] == 66
    assert "garmin" not in out["metrics_by_date"]["2024-03-15"]
    assert "2024-02-01" not in out["metrics_by_date"]
    assert out["last_sync"]["whoop"]["last_data_date"] == "2024-03-15"
    assert out["strong_csv_last_workout_date"] is None
