"""LLM-powered health briefing generator.

Sends structured health context to OpenRouter/Claude and returns
a formatted briefing for Telegram delivery.
"""

import json
import logging
from datetime import date, datetime
from typing import Optional

import requests

from briefing.trends import get_all_trends, format_trends_block, MetricTrend
from config import LLM_MODEL, OPENROUTER_API_KEY
from database import get_db, get_recent_workouts

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

DAILY_SYSTEM_PROMPT = """You are a concise personal health analyst. Given the user's health data from multiple wearables, provide a brief daily health briefing.

Rules:
- Identify the top trend (positive or negative)
- Flag any concerns (declining HRV, signs of overtraining, poor sleep trends)
- Give ONE specific, actionable recommendation
- Keep it under 200 words
- Do NOT repeat raw numbers — the user already sees those above your analysis
- If data from a source is missing, acknowledge it briefly but don't speculate
- Use a supportive, direct tone"""

WEEKLY_SYSTEM_PROMPT = """You are a personal health analyst providing a weekly deep-dive review. Given 7 days of health data from multiple wearables and workout logs, provide a comprehensive weekly briefing.

Rules:
- Summarize the week's key trends across all sources
- Compare this week vs the 30-day baseline
- Flag any patterns (overtraining, insufficient recovery, sleep debt)
- Identify what went well and what needs attention
- Give 2-3 specific, actionable recommendations for next week
- Keep it under 400 words
- Do NOT repeat raw numbers
- If data from a source is missing, acknowledge it but don't speculate
- Use a supportive, coaching tone"""


def _build_context(trends: list[MetricTrend], weekly: bool = False, db_path: Optional[str] = None) -> str:
    """Build the structured data context for the LLM prompt."""
    parts = []

    # Date info
    today = date.today()
    parts.append(f"Date: {today.strftime('%A, %B %d, %Y')}")
    if weekly:
        parts.append("Report type: Weekly deep-dive (last 7 days vs 30-day baseline)")
    else:
        parts.append("Report type: Daily briefing")

    parts.append("")

    # Trends block
    trends_text = format_trends_block(trends)
    parts.append("=== HEALTH METRICS ===")
    parts.append(trends_text)
    parts.append("")

    # Missing sources
    missing = [t.source for t in trends if not t.available]
    if missing:
        unique_missing = sorted(set(missing))
        parts.append(f"Missing data sources: {', '.join(unique_missing)}")
        parts.append("")

    # Recent workouts
    db_kwargs = {"db_path": db_path} if db_path else {}
    with get_db(**db_kwargs) as conn:
        days = 7 if weekly else 3
        workouts = get_recent_workouts(conn, days=days)

    if workouts:
        parts.append("=== RECENT WORKOUTS ===")
        # Group by date and workout
        by_workout = {}
        for w in workouts:
            key = (w["date"], w["workout_name"])
            by_workout.setdefault(key, []).append(w)

        for (dt, name), sets in by_workout.items():
            exercises = set(s["exercise"] for s in sets)
            total_vol = sum(s["volume"] for s in sets if s["volume"])
            best_1rm = max((s["estimated_1rm"] for s in sets if s["estimated_1rm"]), default=0)
            parts.append(f"  {dt} — {name}: {len(exercises)} exercises, "
                        f"{len(sets)} sets, {total_vol:.0f} total volume, "
                        f"best est. 1RM: {best_1rm:.0f}")
    else:
        parts.append("No recent workouts logged.")

    return "\n".join(parts)


def generate_briefing(weekly: bool = False, db_path: Optional[str] = None) -> dict:
    """Generate an LLM health briefing.

    Returns:
        dict with keys: 'trends_block', 'analysis', 'full_message'
    """
    trends = get_all_trends(db_path)
    context = _build_context(trends, weekly=weekly, db_path=db_path)
    trends_block = format_trends_block(trends)

    system_prompt = WEEKLY_SYSTEM_PROMPT if weekly else DAILY_SYSTEM_PROMPT

    # Call LLM
    analysis = _call_llm(system_prompt, context)

    # Build full Telegram message
    header = "📋 Weekly Health Report" if weekly else "🌅 Daily Health Briefing"
    today = date.today().strftime("%A, %B %d")

    full_message = f"{header}\n{today}\n{'━' * 24}\n\n{trends_block}\n\n{'━' * 24}\n💡 Analysis:\n{analysis}"

    return {
        "trends_block": trends_block,
        "analysis": analysis,
        "full_message": full_message,
    }


def _call_llm(system_prompt: str, user_content: str) -> str:
    """Call OpenRouter API for LLM analysis."""
    if not OPENROUTER_API_KEY:
        return "(LLM analysis unavailable — OPENROUTER_API_KEY not set)"

    try:
        resp = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                "max_tokens": 600,
                "temperature": 0.3,
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.RequestException as e:
        logger.error("LLM API call failed: %s", e)
        return f"(Analysis unavailable — API error: {e})"
    except (KeyError, IndexError) as e:
        logger.error("Unexpected LLM response format: %s", e)
        return "(Analysis unavailable — unexpected response format)"
