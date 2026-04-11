"""LLM-powered health briefing generator.

Sends structured health context to OpenRouter/Claude and returns
a formatted briefing for Telegram delivery.
"""

import json
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Optional

import requests

from briefing.trends import get_all_trends, format_trends_block, MetricTrend
from config import LLM_MODEL, OPENROUTER_API_KEY
from database import get_db, get_recent_workouts, get_metrics, get_metric_average

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

DAILY_SYSTEM_PROMPT = """You are a world-class functional medicine practitioner and health coach. You have access to this person's wearable data and workout history. They can already see their scores in their apps — never restate them.

Your job is to catch what they'd MISS:
- HRV-to-training-load mismatches (nervous system not recovering despite "good" sleep scores)
- Patterns across days (e.g. HRV consistently drops after back-to-back training days)
- Signs of accumulated fatigue vs acute fatigue
- Muscle group imbalances or neglected movement patterns
- Strength plateaus or regressions that signal programming issues
- Recovery quality vs recovery quantity (high sleep score but low HRV = poor parasympathetic recovery)
- Overreaching signals before they become overtraining

Rules:
- 1-3 sentences ONLY. Respect their time.
- NEVER restate numbers or scores — they have apps for that
- Only message if there's something genuinely worth flagging
- If nothing stands out, say "Nothing flagged today." and stop
- Skip pleasantries. Direct. Clinical. Useful.
- Think like a practitioner reviewing labs, not a cheerleader"""

WEEKLY_SYSTEM_PROMPT = """You are a world-class functional medicine practitioner doing a weekly review. The user sees their daily scores already — never restate them.

Find the patterns that only emerge across a full week:
- Nervous system recovery trajectory (is HRV trending up, flat, or declining over the week?)
- Training load vs recovery capacity mismatch
- Sleep debt accumulation (subtle declines across multiple nights)
- Muscle group balance and movement pattern gaps
- Volume progression or regression vs prior weeks
- Whether their training frequency matches their recovery capacity

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

    # Workout analysis — much richer context
    with get_db(**db_kwargs) as conn:
        lookback = 30 if weekly else 14
        workouts = get_recent_workouts(conn, days=lookback)

    if workouts:
        parts.append("=== WORKOUT ANALYSIS ===")

        # Group by date and workout
        by_workout = defaultdict(list)
        for w in workouts:
            by_workout[(w["date"], w["workout_name"])].append(w)

        # Training frequency
        workout_dates = sorted(set(w["date"] for w in workouts))
        parts.append(f"Training frequency: {len(workout_dates)} sessions in last {lookback} days")

        # Days since last workout
        if workout_dates:
            last_workout = date.fromisoformat(workout_dates[-1])
            days_rest = (today - last_workout).days
            parts.append(f"Days since last workout: {days_rest}")

        # Muscle group / exercise frequency
        exercise_counts = defaultdict(int)
        exercise_max_weight = defaultdict(float)
        exercise_max_1rm = defaultdict(float)
        weekly_volume = defaultdict(float)

        for (dt, name), sets in by_workout.items():
            week_key = date.fromisoformat(dt).isocalendar()[1]
            for s in sets:
                ex = s["exercise"]
                exercise_counts[ex] += 1
                if s["weight"] and s["weight"] > exercise_max_weight[ex]:
                    exercise_max_weight[ex] = s["weight"]
                if s["estimated_1rm"] and s["estimated_1rm"] > exercise_max_1rm[ex]:
                    exercise_max_1rm[ex] = s["estimated_1rm"]
                if s["volume"]:
                    weekly_volume[week_key] += s["volume"]

        # Top exercises by frequency
        top_exercises = sorted(exercise_counts.items(), key=lambda x: -x[1])[:10]
        parts.append(f"Top exercises (last {lookback}d): " +
                    ", ".join(f"{ex}({c} sets)" for ex, c in top_exercises))

        # Volume trend by week
        if len(weekly_volume) > 1:
            sorted_weeks = sorted(weekly_volume.items())
            parts.append("Weekly total volume trend: " +
                        " → ".join(f"wk{w}:{v:.0f}" for w, v in sorted_weeks[-4:]))

        # Best estimated 1RMs for key lifts
        key_lifts = ["Bench Press (Barbell)", "Squat (Barbell)", "Deadlift (Barbell)",
                     "Bench Press (Dumbbell)", "Incline Bench Press (Barbell)",
                     "Squat (Smith Machine)", "Leg Press"]
        prs = {ex: exercise_max_1rm[ex] for ex in key_lifts if exercise_max_1rm.get(ex)}
        if prs:
            parts.append("Best est. 1RMs (last {0}d): ".format(lookback) +
                        ", ".join(f"{ex}: {v:.0f}lb" for ex, v in prs.items()))

        # Recent sessions detail (last 3)
        recent_sessions = sorted(by_workout.items(), key=lambda x: x[0])[-3:]
        parts.append("")
        parts.append("=== LAST 3 SESSIONS ===")
        for (dt, name), sets in recent_sessions:
            exercises = set(s["exercise"] for s in sets)
            total_vol = sum(s["volume"] for s in sets if s["volume"])
            parts.append(f"  {dt} — {name}: {', '.join(sorted(exercises))} | vol: {total_vol:.0f}")
    else:
        parts.append("No workouts in the last {0} days.".format(lookback))

    return "\n".join(parts)


def _get_todays_key_metrics(db_path: Optional[str] = None) -> str:
    """Get today's most important metrics as a compact one-liner."""
    db_kwargs = {"db_path": db_path} if db_path else {}
    today_str = date.today().isoformat()
    yesterday_str = (date.today() - timedelta(days=1)).isoformat()

    parts = []
    with get_db(**db_kwargs) as conn:
        # Check today first, then yesterday
        for dt in [today_str, yesterday_str]:
            metrics = conn.execute(
                "SELECT metric_name, value, source FROM health_metrics WHERE date = ? AND value IS NOT NULL",
                (dt,)
            ).fetchall()
            if metrics:
                metric_map = {(r["source"], r["metric_name"]): r["value"] for r in metrics}

                # Key metrics in priority order
                recovery = metric_map.get(("whoop", "recovery_score"))
                sleep = metric_map.get(("oura", "sleep_score"))
                hrv_whoop = metric_map.get(("whoop", "hrv_rmssd"))
                hrv_oura = metric_map.get(("oura", "hrv_average"))
                strain = metric_map.get(("whoop", "strain_score"))
                readiness = metric_map.get(("oura", "readiness_score"))

                if recovery is not None:
                    parts.append(f"Recovery: {recovery:.0f}%")
                if sleep is not None:
                    parts.append(f"Sleep: {sleep:.0f}")
                if readiness is not None:
                    parts.append(f"Readiness: {readiness:.0f}")
                hrv = hrv_whoop or hrv_oura
                if hrv is not None:
                    parts.append(f"HRV: {hrv:.0f}ms")
                if strain is not None:
                    parts.append(f"Strain: {strain:.1f}")
                break  # Found data, stop looking

    return " | ".join(parts) if parts else ""


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
