"""LLM-powered health briefing generator.

Sends structured health context to OpenRouter/Claude and returns
a formatted briefing for Telegram delivery.
"""

import json
import logging
from datetime import date, datetime, timedelta
from typing import Optional

import requests

from briefing.trends import get_all_trends, format_trends_block, MetricTrend
from config import LLM_MODEL, OPENROUTER_API_KEY
from database import get_db, get_metrics, get_metric_average

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

DAILY_SYSTEM_PROMPT = """You are a world-class functional medicine practitioner and health coach. You have access to this person's wearable data (Oura + Whoop). They can already see their scores in their apps — never restate them.

IMPORTANT: Do NOT comment on workout volume, training frequency, or whether they "skipped" training. The user does not log every workout in Strong, so workout-log absence is meaningless. Whoop strain captures all real training load automatically — use that as the signal of training stress, never a strength-training log.

Your job is to catch what they'd MISS:
- HRV-to-strain mismatches (nervous system not recovering despite "good" sleep scores)
- Patterns across days (e.g. HRV consistently drops after back-to-back high-strain days)
- Signs of accumulated fatigue vs acute fatigue
- Recovery quality vs recovery quantity (high sleep score but low HRV = poor parasympathetic recovery)
- Overreaching signals before they become overtraining

Rules:
- 1-3 sentences ONLY. Respect their time.
- NEVER restate numbers or scores — they have apps for that
- Only message if there's something genuinely worth flagging
- If nothing stands out, say "Nothing flagged today." and stop
- Skip pleasantries. Direct. Useful.
- Be measured — flag concerns proportionally, don't catastrophize
- Think like a practitioner reviewing labs, not an alarmist"""

WEEKLY_SYSTEM_PROMPT = """You are a world-class functional medicine practitioner doing a weekly review. The user sees their daily scores already — never restate them.

IMPORTANT: Do NOT comment on workout volume, "missed" training days, or strength-training programming. The user doesn't log every workout in Strong. Whoop strain captures actual training load automatically — anchor your analysis on Whoop strain + Oura activity, never on a strength log.

Find the patterns that only emerge across a full week:
- Nervous system recovery trajectory (is HRV trending up, flat, or declining over the week?)
- Cumulative strain vs recovery capacity mismatch
- Sleep debt accumulation (subtle declines across multiple nights)
- Whether their average daily strain matches their average recovery

Rules:
- 4-6 sentences MAX. Lead with the most important finding.
- 1-2 specific changes for next week
- NEVER restate raw numbers — only patterns and implications
- If it was a solid week, say so in one sentence and move on
- Clinical, direct. No cheerleading."""


def _build_context(trends: list[MetricTrend], weekly: bool = False, db_path: Optional[str] = None) -> str:
    """Build rich structured data context for the LLM prompt."""
    parts = []
    today = date.today()
    db_kwargs = {"db_path": db_path} if db_path else {}

    parts.append(f"Date: {today.strftime('%A, %B %d, %Y')}")
    parts.append("")

    # Current metrics with 7d and 30d context
    parts.append("=== HEALTH METRICS (7-day avg → 30-day avg) ===")
    for t in trends:
        if t.available:
            val_30d = f"{t.avg_30d:.0f}" if t.avg_30d else "n/a"
            parts.append(f"  {t.metric_name} ({t.source}): 7d={t.avg_7d:.1f}, 30d={val_30d} {t.arrow}")
    parts.append("")

    # NOTE: Strong workout history intentionally excluded from analysis.
    # The user does not log every session in Strong, so workout-log gaps
    # are not a real signal of training absence. Whoop strain captures
    # actual training load automatically — that's what the prompts use.

    return "\n".join(parts)


def _get_todays_key_metrics(db_path: Optional[str] = None) -> str:
    """Get today's most important metrics, grouped by source.

    Checks both today and yesterday since Oura dates sleep to the
    night it started (yesterday), while readiness/activity are today.
    """
    db_kwargs = {"db_path": db_path} if db_path else {}
    today_str = date.today().isoformat()
    yesterday_str = (date.today() - timedelta(days=1)).isoformat()

    with get_db(**db_kwargs) as conn:
        # Get last 2 days of metrics to build complete picture
        metrics = conn.execute(
            "SELECT metric_name, value, source, date FROM health_metrics "
            "WHERE date >= ? AND value IS NOT NULL ORDER BY date DESC",
            (yesterday_str,)
        ).fetchall()

        if not metrics:
            return ""

        # Build map preferring today's data, falling back to yesterday
        metric_map = {}
        for r in metrics:
            key = (r["source"], r["metric_name"])
            if key not in metric_map:  # First seen = most recent
                metric_map[key] = r["value"]

        lines = []

        # Oura line
        oura_parts = []
        sleep = metric_map.get(("oura", "sleep_score"))
        readiness = metric_map.get(("oura", "readiness_score"))
        activity = metric_map.get(("oura", "activity_score"))
        hrv_oura = metric_map.get(("oura", "hrv_average"))
        rhr_oura = metric_map.get(("oura", "readiness_resting_heart_rate"))
        if sleep is not None:
            oura_parts.append(f"Sleep: {sleep:.0f}")
        if readiness is not None:
            oura_parts.append(f"Readiness: {readiness:.0f}")
        if activity is not None:
            oura_parts.append(f"Activity: {activity:.0f}")
        if hrv_oura is not None:
            oura_parts.append(f"HRV: {hrv_oura:.0f}ms")
        if rhr_oura is not None:
            oura_parts.append(f"RHR: {rhr_oura:.0f}")
        if oura_parts:
            lines.append(f"Oura: {' | '.join(oura_parts)}")

        # Whoop line
        whoop_parts = []
        recovery = metric_map.get(("whoop", "recovery_score"))
        strain = metric_map.get(("whoop", "strain_score"))
        hrv_whoop = metric_map.get(("whoop", "hrv_rmssd"))
        rhr = metric_map.get(("whoop", "resting_heart_rate"))
        max_hr = metric_map.get(("whoop", "max_heart_rate"))
        cals = metric_map.get(("whoop", "kilojoules"))
        if recovery is not None:
            whoop_parts.append(f"Recovery: {recovery:.0f}%")
        if strain is not None:
            whoop_parts.append(f"Strain: {strain:.1f}")
        if hrv_whoop is not None:
            whoop_parts.append(f"HRV: {hrv_whoop:.0f}ms")
        if rhr is not None:
            whoop_parts.append(f"RHR: {rhr:.0f}bpm")
        if max_hr is not None:
            whoop_parts.append(f"Max HR: {max_hr:.0f}")
        if cals is not None:
            whoop_parts.append(f"Cal: {cals / 4.184:.0f}kcal")
        if whoop_parts:
            lines.append(f"Whoop: {' | '.join(whoop_parts)}")

        return "\n".join(lines) if lines else ""


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
    today = date.today().strftime("%A, %B %d")

    if weekly:
        full_message = f"📋 Weekly Review — {today}\n\n{analysis}"
    else:
        key_metrics = _get_todays_key_metrics(db_path)
        if key_metrics:
            full_message = f"{key_metrics}\n\n{analysis}"
        else:
            full_message = f"💡 {analysis}"

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
                "max_tokens": 400,
                "temperature": 0.4,
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
