"""Tests for trend calculation."""

from briefing.trends import (
    compute_arrow, format_value, get_all_trends,
    format_trends_block, MetricTrend,
)


def test_arrow_up():
    """7-day avg significantly above 30-day → ↑."""
    assert compute_arrow(110, 100) == "↑"


def test_arrow_down():
    """7-day avg significantly below 30-day → ↓."""
    assert compute_arrow(90, 100) == "↓"


def test_arrow_stable():
    """7-day avg close to 30-day → →."""
    assert compute_arrow(101, 100) == "→"


def test_arrow_missing_data():
    """Missing data → —."""
    assert compute_arrow(None, 100) == "—"
    assert compute_arrow(100, None) == "—"


def test_arrow_zero_baseline():
    """Zero baseline → —."""
    assert compute_arrow(100, 0) == "—"


def test_format_value_integer():
    """Format as integer."""
    assert format_value(85.3, "", 0) == "85"


def test_format_value_decimal():
    """Format with decimals."""
    assert format_value(8.5, "", 1) == "8.5"


def test_format_value_with_unit():
    """Format with unit suffix."""
    assert format_value(45, "ms", 0) == "45ms"


def test_format_value_none():
    """None value → —."""
    assert format_value(None) == "—"


def test_get_all_trends_populated(populated_db):
    """get_all_trends returns trends for all tracked metrics."""
    trends = get_all_trends(populated_db)
    assert len(trends) > 0
    available = [t for t in trends if t.available]
    assert len(available) > 0


def test_get_all_trends_empty(tmp_db):
    """get_all_trends with empty DB returns trends with None averages."""
    trends = get_all_trends(tmp_db)
    assert len(trends) > 0
    assert all(not t.available for t in trends)


def test_format_trends_block_populated(populated_db):
    """format_trends_block produces readable output."""
    trends = get_all_trends(populated_db)
    block = format_trends_block(trends)
    assert "Oura" in block or "Whoop" in block or "Garmin" in block


def test_format_trends_block_empty(tmp_db):
    """format_trends_block with no data shows missing sources."""
    trends = get_all_trends(tmp_db)
    block = format_trends_block(trends)
    assert "No data" in block
