"""Tests for the Strong app CSV parser."""

import pytest

from parsers.strong import epley_1rm, compute_volume, parse_csv, _normalize_date


def test_epley_1rm_standard():
    """Epley formula: 100kg × 8 reps → ~126.7."""
    result = epley_1rm(100, 8)
    assert abs(result - 126.7) < 0.1


def test_epley_1rm_single():
    """Single rep returns the weight itself."""
    assert epley_1rm(150, 1) == 150


def test_epley_1rm_zero_weight():
    """Zero weight returns 0."""
    assert epley_1rm(0, 8) == 0.0


def test_epley_1rm_zero_reps():
    """Zero reps returns 0."""
    assert epley_1rm(100, 0) == 0.0


def test_compute_volume():
    """Volume = weight × reps."""
    assert compute_volume(100, 8) == 800.0


def test_compute_volume_zero():
    """Zero weight or reps yields 0."""
    assert compute_volume(0, 8) == 0.0
    assert compute_volume(100, 0) == 0.0


def test_parse_csv_basic(sample_strong_csv, tmp_db):
    """Parse a well-formed Strong CSV."""
    result = parse_csv(sample_strong_csv, tmp_db)
    assert result["sets"] == 10
    assert result["exercises"] == 4  # Bench, OHP, Deadlift, Row
    assert result["workouts"] == 2  # Push Day, Pull Day


def test_parse_csv_idempotent(sample_strong_csv, tmp_db):
    """Re-parsing the same CSV produces the same counts (UPSERT)."""
    r1 = parse_csv(sample_strong_csv, tmp_db)
    r2 = parse_csv(sample_strong_csv, tmp_db)
    assert r1["sets"] == r2["sets"]

    # Verify no duplicates in DB
    from database import get_db
    with get_db(tmp_db) as conn:
        count = conn.execute("SELECT COUNT(*) as c FROM workouts").fetchone()["c"]
    assert count == 10


def test_parse_csv_empty(tmp_db):
    """Empty CSV (headers only) returns zero counts."""
    csv_content = "Date,Workout Name,Exercise Name,Set Order,Weight,Reps\n"
    result = parse_csv(csv_content, tmp_db)
    assert result["sets"] == 0


def test_parse_csv_missing_columns(tmp_db):
    """CSV with missing required columns raises ValueError."""
    bad_csv = "Name,Weight\nBench,100\n"
    with pytest.raises(ValueError, match="missing required columns"):
        parse_csv(bad_csv, tmp_db)


def test_normalize_date_iso():
    """ISO format passes through."""
    assert _normalize_date("2024-03-15") == "2024-03-15"


def test_normalize_date_datetime():
    """Datetime string is normalized to date."""
    assert _normalize_date("2024-03-15 10:00:00") == "2024-03-15"
