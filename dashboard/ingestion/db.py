"""Supabase helper — uses the service-role key to bypass RLS for server-side writes."""

import os
from typing import Any

from supabase import Client, create_client


def client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)


def upsert_daily_metric(sb: Client, row: dict[str, Any]) -> None:
    """row keys: date, hrv, rhr, sleep_score, sleep_hours, steps, recovery_score, strain, source, raw"""
    sb.table("daily_metrics").upsert(row, on_conflict="date").execute()


def upsert_sleep_detail(sb: Client, row: dict[str, Any]) -> None:
    sb.table("sleep_detail").upsert(row, on_conflict="date").execute()


def upsert_inbody(sb: Client, row: dict[str, Any]) -> None:
    sb.table("inbody_scans").upsert(row, on_conflict="date").execute()


def insert_workouts(sb: Client, rows: list[dict[str, Any]]) -> None:
    """Strong CSV — bulk insert. Unique constraint (date, exercise, set, reps, weight) prevents dupes."""
    if not rows:
        return
    sb.table("workouts_strong").upsert(
        rows, on_conflict="date,exercise,set_number,reps,weight_lbs"
    ).execute()


def insert_panel(sb: Client, panel: dict[str, Any], markers: list[dict[str, Any]]) -> str:
    """Insert one bloodwork panel + its markers. Returns panel_id."""
    res = sb.table("bloodwork_panels").insert(panel).execute()
    panel_id = res.data[0]["id"]
    for m in markers:
        m["panel_id"] = panel_id
    sb.table("bloodwork_markers").insert(markers).execute()
    return panel_id
