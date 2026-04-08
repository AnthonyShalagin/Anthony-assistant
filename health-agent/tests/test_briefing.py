"""Tests for the LLM health briefing generator."""

from unittest.mock import patch, MagicMock

from briefing.generator import generate_briefing, _build_context, _call_llm
from briefing.trends import get_all_trends


def test_build_context_populated(populated_db):
    """_build_context produces structured text with metric data."""
    trends = get_all_trends(populated_db)
    context = _build_context(trends, weekly=False, db_path=populated_db)
    assert "HEALTH METRICS" in context
    assert "Daily briefing" in context


def test_build_context_weekly(populated_db):
    """Weekly context includes workout data."""
    trends = get_all_trends(populated_db)
    context = _build_context(trends, weekly=True, db_path=populated_db)
    assert "Weekly deep-dive" in context
    assert "RECENT WORKOUTS" in context


def test_build_context_empty(tmp_db):
    """_build_context with empty DB still produces valid context."""
    trends = get_all_trends(tmp_db)
    context = _build_context(trends, db_path=tmp_db)
    assert "HEALTH METRICS" in context
    assert "No recent workouts" in context


@patch("briefing.generator.requests.post")
def test_call_llm_success(mock_post):
    """_call_llm returns LLM response text."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "Your sleep improved this week."}}]
    }
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_post.return_value = mock_resp

    with patch("briefing.generator.OPENROUTER_API_KEY", "fake-key"):
        result = _call_llm("system prompt", "user data")
    assert "sleep improved" in result


@patch("briefing.generator.requests.post")
def test_call_llm_api_error(mock_post):
    """_call_llm handles API errors gracefully."""
    import requests
    mock_post.side_effect = requests.RequestException("timeout")

    with patch("briefing.generator.OPENROUTER_API_KEY", "fake-key"):
        result = _call_llm("system prompt", "user data")
    assert "unavailable" in result.lower()


def test_call_llm_no_api_key():
    """_call_llm returns fallback when no API key is set."""
    with patch("briefing.generator.OPENROUTER_API_KEY", ""):
        result = _call_llm("system", "user")
    assert "unavailable" in result.lower()


@patch("briefing.generator._call_llm")
def test_generate_briefing_daily(mock_llm, populated_db):
    """generate_briefing produces a full daily message."""
    mock_llm.return_value = "Your HRV is trending up. Keep it up!"
    result = generate_briefing(weekly=False, db_path=populated_db)

    assert "trends_block" in result
    assert "analysis" in result
    assert "full_message" in result
    assert "Daily Health Briefing" in result["full_message"]


@patch("briefing.generator._call_llm")
def test_generate_briefing_weekly(mock_llm, populated_db):
    """generate_briefing produces a full weekly message."""
    mock_llm.return_value = "Great week overall. Recovery is strong."
    result = generate_briefing(weekly=True, db_path=populated_db)
    assert "Weekly Health Report" in result["full_message"]
