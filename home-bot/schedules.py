"""Schedule management for home automation.

Supports thermostat and lock schedules. Each schedule has an
action_type ('thermostat' or 'lock') and a JSON payload of params.
"""

import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# Resolve DB path relative to this file — works whether imported from
# home-bot directly or reused from Jarvis.
DB_PATH = str(Path(__file__).resolve().parent / "data" / "schedules.db")

ET = ZoneInfo("America/New_York")

SCHEMA = """
CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    action_type TEXT NOT NULL DEFAULT 'thermostat',  -- 'thermostat' or 'lock'
    params TEXT NOT NULL DEFAULT '{}',                -- JSON payload
    time TEXT NOT NULL,
    days TEXT NOT NULL DEFAULT 'daily',
    active INTEGER NOT NULL DEFAULT 1,
    -- legacy columns kept for backward compat
    temperature INTEGER,
    mode TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


def init_db():
    """Create or migrate the schedules database."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)

    # Migration: add action_type and params columns if the DB is old
    existing_cols = {r[1] for r in conn.execute("PRAGMA table_info(schedules)").fetchall()}
    if "action_type" not in existing_cols:
        conn.execute("ALTER TABLE schedules ADD COLUMN action_type TEXT NOT NULL DEFAULT 'thermostat'")
    if "params" not in existing_cols:
        conn.execute("ALTER TABLE schedules ADD COLUMN params TEXT NOT NULL DEFAULT '{}'")

    # Backfill params from legacy temperature/mode columns
    rows = conn.execute("SELECT id, temperature, mode, params FROM schedules").fetchall()
    for row in rows:
        sched_id, temp, mode, params = row
        if (not params or params == '{}') and temp is not None:
            payload = json.dumps({"temperature": temp, "mode": mode or "cool"})
            conn.execute("UPDATE schedules SET params = ? WHERE id = ?", (payload, sched_id))

    conn.commit()
    conn.close()


def add_schedule(name: str, temperature: int, mode: str, time_str: str,
                 days: str = "daily") -> str:
    """Add a thermostat schedule (back-compat helper)."""
    return add_thermostat_schedule(name, temperature, mode, time_str, days)


def add_thermostat_schedule(name: str, temperature: int, mode: str,
                            time_str: str, days: str = "daily") -> str:
    """Add a recurring thermostat schedule."""
    params = json.dumps({"temperature": temperature, "mode": mode})
    return _insert_schedule(name, "thermostat", params, time_str, days,
                            legacy={"temperature": temperature, "mode": mode})


def add_lock_schedule(name: str, locked: bool, time_str: str,
                      days: str = "daily") -> str:
    """Add a recurring lock schedule. locked=True to lock, False to unlock."""
    params = json.dumps({"locked": locked})
    action = "lock" if locked else "unlock"
    result = _insert_schedule(name, "lock", params, time_str, days)
    if result.startswith("Schedule created"):
        return f'Lock schedule created: "{name}" — {action} at {time_str}, {days}.'
    return result


def _insert_schedule(name: str, action_type: str, params: str, time_str: str,
                     days: str, legacy: Optional[dict] = None) -> str:
    conn = sqlite3.connect(DB_PATH)
    try:
        legacy = legacy or {}
        conn.execute(
            "INSERT INTO schedules (name, action_type, params, time, days, temperature, mode) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, action_type, params, time_str, days,
             legacy.get("temperature"), legacy.get("mode")),
        )
        conn.commit()
        if action_type == "thermostat":
            meta = json.loads(params)
            return (f'Schedule created: "{name}" — {meta["temperature"]}°F '
                    f'({meta["mode"]}) at {time_str}, {days}.')
        return f'Schedule created: "{name}"'
    except sqlite3.IntegrityError:
        return f'Schedule "{name}" already exists. Delete it first or use a different name.'
    finally:
        conn.close()


def delete_schedule(name: str) -> str:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("DELETE FROM schedules WHERE LOWER(name) = LOWER(?)", (name,))
    conn.commit()
    conn.close()
    if cursor.rowcount > 0:
        return f'Deleted "{name}" schedule.'
    return f'Schedule "{name}" not found.'


def list_schedules() -> str:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM schedules ORDER BY time").fetchall()
    conn.close()

    if not rows:
        return "No schedules set."

    lines = ["Your schedules:"]
    for i, r in enumerate(rows, 1):
        status = "✅" if r["active"] else "⏸️"
        action_type = r["action_type"] or "thermostat"
        try:
            params = json.loads(r["params"]) if r["params"] else {}
        except (json.JSONDecodeError, TypeError):
            params = {}

        if action_type == "thermostat":
            temp = params.get("temperature") or r["temperature"]
            mode = params.get("mode") or r["mode"] or "cool"
            desc = f'{temp}°F ({mode})'
        elif action_type == "lock":
            desc = "lock" if params.get("locked") else "unlock"
        else:
            desc = action_type

        lines.append(
            f'  {i}. {r["name"]} — {desc} at {r["time"]}, {r["days"]} {status}'
        )
    return "\n".join(lines)


WEEKDAYS = {"monday", "tuesday", "wednesday", "thursday", "friday"}
WEEKENDS = {"saturday", "sunday"}


def _day_matches(days_spec: str, current_day: str) -> bool:
    days = days_spec.lower().strip()
    if days == "daily":
        return True
    if days == "weekdays":
        return current_day in WEEKDAYS
    if days == "weekends":
        return current_day in WEEKENDS
    day_set = {d.strip() for d in days.split(",")}
    return current_day in day_set


def get_due_schedules() -> list[dict]:
    """Get schedules that should run right now."""
    now = datetime.now(ET)
    current_time = now.strftime("%I:%M %p").lstrip("0")
    current_day = now.strftime("%A").lower()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM schedules WHERE active = 1").fetchall()
    conn.close()

    due = []
    for r in rows:
        sched_time = r["time"].strip().upper()
        if _times_match(sched_time, current_time) and _day_matches(r["days"], current_day):
            entry = dict(r)
            try:
                entry["params_dict"] = json.loads(r["params"]) if r["params"] else {}
            except (json.JSONDecodeError, TypeError):
                entry["params_dict"] = {}
            # Back-compat: populate from legacy columns if params is empty
            if not entry["params_dict"] and r["temperature"] is not None:
                entry["params_dict"] = {
                    "temperature": r["temperature"],
                    "mode": r["mode"] or "cool",
                }
            due.append(entry)
    return due


def _times_match(sched_time: str, current_time: str) -> bool:
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
