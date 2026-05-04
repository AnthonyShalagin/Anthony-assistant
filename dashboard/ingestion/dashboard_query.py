"""Helpers for Jarvis to query the dashboard DB.

Wire into jarvis/tools.py by importing this module and adding the schema
in TOOL_SCHEMAS plus a branch in call_tool(). See dashboard/JARVIS_INTEGRATION.md.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from db import client


def latest_metrics() -> dict[str, Any]:
    """Most recent daily_metrics row."""
    sb = client()
    res = (
        sb.table("daily_metrics")
        .select("*")
        .order("date", desc=True)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else {}


def metrics_range(days: int = 7) -> list[dict[str, Any]]:
    """Last N days of daily_metrics, oldest → newest."""
    sb = client()
    start = (date.today() - timedelta(days=days)).isoformat()
    res = (
        sb.table("daily_metrics")
        .select("*")
        .gte("date", start)
        .order("date")
        .execute()
    )
    return res.data or []


def goal_progress() -> list[dict[str, Any]]:
    """Compute current weekly avg steps/sleep + latest BF for active goals."""
    sb = client()
    goals = sb.table("goals").select("*").eq("active", True).execute().data or []
    last7 = metrics_range(7)
    if not last7:
        return goals

    steps_avg = sum(m.get("steps") or 0 for m in last7) / len(last7)
    sleep_avg = sum(m.get("sleep_hours") or 0 for m in last7) / len(last7)

    inbody = (
        sb.table("inbody_scans").select("*").order("date", desc=True).limit(1).execute().data
    )
    bf = inbody[0]["bf_pct"] if inbody else None

    out = []
    for g in goals:
        cur: float | None
        if g["metric"] == "steps":
            cur = steps_avg
        elif g["metric"] == "sleep":
            cur = sleep_avg
        elif g["metric"] == "bf":
            cur = bf
        else:
            cur = None
        cmp_ = g.get("comparison", "gte")
        hit = cur is not None and (cur >= g["target"] if cmp_ == "gte" else cur <= g["target"])
        out.append({**g, "current": cur, "hit": hit})
    return out


def recent_prs(weeks: int = 8) -> list[dict[str, Any]]:
    """Best e1RM per exercise in the last N weeks."""
    sb = client()
    start = (date.today() - timedelta(weeks=weeks)).isoformat()
    res = (
        sb.table("workouts_strong")
        .select("date,exercise,weight_lbs,e1rm,reps")
        .gte("date", start)
        .order("e1rm", desc=True)
        .execute()
    )
    rows = res.data or []
    seen: dict[str, dict] = {}
    for r in rows:
        if r["exercise"] not in seen:
            seen[r["exercise"]] = r
    return list(seen.values())


def latest_bloodwork() -> dict[str, Any]:
    sb = client()
    panels = (
        sb.table("bloodwork_panels").select("*").order("panel_date", desc=True).limit(1).execute().data
    )
    if not panels:
        return {}
    panel = panels[0]
    markers = (
        sb.table("bloodwork_markers").select("*").eq("panel_id", panel["id"]).execute().data or []
    )
    return {"panel": panel, "markers": markers}
