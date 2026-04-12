"""Schedule management for thermostat automation."""

import sqlite3
import threading
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from config import DB_PATH

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")

SCHEMA = """
CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    temperature INTEGER NOT NULL,
    mode TEXT NOT NULL DEFAULT 'cool',
    time TEXT NOT NULL,
    days TEXT NOT NULL DEFAULT 'daily',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


def init_db():
    """Create the schedules database."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.close()


def add_schedule(name: str, temperature: int, mode: str, time_str: str,
                 days: str = "daily") -> str:
    """Add a new schedule."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT INTO schedules (name, temperature, mode, time, days) VALUES (?, ?, ?, ?, ?)",
            (name, temperature, mode, time_str, days),
        )
        conn.commit()
        return f'Schedule created: "{name}" — {temperature}°F ({mode}) at {time_str}, {days}.'
    except sqlite3.IntegrityError:
        return f'Schedule "{name}" already exists. Delete it first or use a different name.'
    finally:
        conn.close()


def delete_schedule(name: str) -> str:
    """Delete a schedule by name."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("DELETE FROM schedules WHERE LOWER(name) = LOWER(?)", (name,))
    conn.commit()
    conn.close()
    if cursor.rowcount > 0:
        return f'Deleted "{name}" schedule.'
    return f'Schedule "{name}" not found.'


def list_schedules() -> str:
    """List all schedules."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM schedules ORDER BY time").fetchall()
    conn.close()

    if not rows:
        return "No schedules set."

    lines = ["Your schedules:"]
    for i, r in enumerate(rows, 1):
        status = "✅" if r["active"] else "⏸️"
        lines.append(
            f'  {i}. {r["name"]} — {r["temperature"]}°F ({r["mode"]}) '
            f'at {r["time"]}, {r["days"]} {status}'
        )
    return "\n".join(lines)


WEEKDAYS = {"monday", "tuesday", "wednesday", "thursday", "friday"}
WEEKENDS = {"saturday", "sunday"}


def _day_matches(days_spec: str, current_day: str) -> bool:
    """Check if the schedule's day spec matches today."""
    days = days_spec.lower().strip()
    if days == "daily":
        return True
    if days == "weekdays":
        return current_day in WEEKDAYS
    if days == "weekends":
        return current_day in WEEKENDS
    # Comma-separated list
    day_set = {d.strip() for d in days.split(",")}
    return current_day in day_set


def get_due_schedules() -> list[dict]:
    """Get schedules that should run right now."""
    now = datetime.now(ET)
    current_time = now.strftime("%I:%M %p").lstrip("0")
    current_day = now.strftime("%A").lower()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM schedules WHERE active = 1"
    ).fetchall()
    conn.close()

    due = []
    for r in rows:
        sched_time = r["time"].strip().upper()
        if _times_match(sched_time, current_time):
            if _day_matches(r["days"], current_day):
                due.append(dict(r))
    return due


def _times_match(sched_time: str, current_time: str) -> bool:
    """Check if schedule time matches current time (ignoring seconds)."""
    try:
        s = datetime.strptime(sched_time, "%I:%M %p").strftime("%H:%M")
        c = datetime.strptime(current_time, "%I:%M %p").strftime("%H:%M")
        return s == c
    except ValueError:
        try:
            s = datetime.strptime(sched_time, "%H:%M").strftime("%H:%M")
            c = datetime.strptime(current_time, "%I:%M %p").strftime("%H:%M")
            return s == c
        except ValueError:
            return False
