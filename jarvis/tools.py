"""Tools that the LLM orchestrator can call.

Each tool wraps functionality from one of the existing bots
(genesis-bot, health-agent, home-bot) so Jarvis can route
requests across domains in a single conversation.
"""

import asyncio
import json
import logging
import sys
from datetime import date, timedelta
from typing import Optional

import requests

from config import (
    GENESIS_SERVICE_URL, HEALTH_AGENT_DIR, GENESIS_BOT_DIR, HOME_BOT_DIR,
    HEALTH_DB_PATH, ZIP_CODE,
)

logger = logging.getLogger(__name__)

# Add sibling bot directories to sys.path so we can import their modules
for path in (str(HEALTH_AGENT_DIR), str(GENESIS_BOT_DIR), str(HOME_BOT_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)


# ---------- GENESIS (Car) ----------

def car_command(command: str) -> dict:
    """Send a command to the Genesis GV70.

    Args:
        command: One of 'start', 'start-winter', 'start-summer',
                 'stop', 'lock', 'unlock', 'status'.
    """
    try:
        resp = requests.post(
            f"{GENESIS_SERVICE_URL}/command",
            json={"command": command},
            timeout=120,
        )
        return resp.json()
    except Exception as e:
        return {"success": False, "message": f"Car service error: {e}"}


def car_auto_start() -> dict:
    """Start the car with weather-based climate preset (winter/summer/mild)."""
    # Inline weather check (reuse genesis-bot logic)
    try:
        from weather import auto_detect_command, get_current_temp
        command = auto_detect_command()
        temp = get_current_temp()
    except Exception as e:
        logger.warning("Weather detection failed: %s", e)
        command = "start"
        temp = None

    result = car_command(command)
    result["chosen_command"] = command
    if temp is not None:
        result["current_temp_f"] = temp
    return result


# ---------- HEALTH AGENT ----------

def health_briefing(weekly: bool = False) -> dict:
    """Generate a daily or weekly health briefing using Oura + Whoop data.

    Args:
        weekly: If True, generate a weekly deep-dive review.
    """
    try:
        from briefing.generator import generate_briefing
        result = generate_briefing(weekly=weekly, db_path=HEALTH_DB_PATH)
        return {"success": True, "message": result["full_message"]}
    except Exception as e:
        return {"success": False, "message": f"Briefing failed: {e}"}


def health_ask(question: str) -> dict:
    """Answer a natural language question about the user's health data.

    Uses Oura, Whoop, and workout history from the past 14-30 days.
    """
    try:
        from telegram_bot import handle_question
        answer = handle_question(question, db_path=HEALTH_DB_PATH)
        return {"success": True, "message": answer}
    except Exception as e:
        return {"success": False, "message": f"Health Q&A failed: {e}"}


def health_pull_now() -> dict:
    """Force-pull the latest Oura and Whoop data right now."""
    messages = []
    try:
        from clients.oura import pull_daily as oura_pull
        today = date.today().isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        r = oura_pull(yesterday, db_path=HEALTH_DB_PATH)
        oura_pull(today, db_path=HEALTH_DB_PATH)
        messages.append(f"Oura: {len([k for k in r if not k.endswith('_error')])} metrics")
    except Exception as e:
        messages.append(f"Oura error: {e}")

    try:
        from clients.whoop import pull_daily as whoop_pull
        today = date.today().isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        r = whoop_pull(yesterday, db_path=HEALTH_DB_PATH)
        whoop_pull(today, db_path=HEALTH_DB_PATH)
        messages.append(f"Whoop: {len([k for k in r if not k.endswith('_error')])} metrics")
    except Exception as e:
        messages.append(f"Whoop error: {e}")

    return {"success": True, "message": " | ".join(messages)}


# ---------- HOME (SmartRent) ----------

def _run_async(coro):
    """Run async coroutine in a sync context (reuses home-bot's helper)."""
    try:
        from smart_home import run_async
        return run_async(coro)
    except Exception as e:
        logger.error("async run failed: %s", e)
        raise


def home_thermostat_status() -> dict:
    """Get current thermostat temperature, humidity, mode, and setpoint."""
    try:
        from smart_home import get_thermostat_status
        status = _run_async(get_thermostat_status())
        return {"success": True, "data": status}
    except Exception as e:
        return {"success": False, "message": f"Thermostat error: {e}"}


def home_thermostat_set(temperature: int, mode: str = "cool") -> dict:
    """Set thermostat to a temperature in a given mode.

    Args:
        temperature: Target temperature in Fahrenheit (60-85).
        mode: 'cool', 'heat', 'auto', or 'off'.
    """
    try:
        from smart_home import set_thermostat
        msg = _run_async(set_thermostat(temperature, mode))
        return {"success": True, "message": msg}
    except Exception as e:
        return {"success": False, "message": f"Thermostat set error: {e}"}


def home_lock_status() -> dict:
    """Check whether the front door is locked."""
    try:
        from smart_home import get_lock_status
        status = _run_async(get_lock_status())
        return {"success": True, "data": status}
    except Exception as e:
        return {"success": False, "message": f"Lock error: {e}"}


def home_lock_set(locked: bool) -> dict:
    """Lock or unlock the front door.

    Args:
        locked: True to lock, False to unlock.
    """
    try:
        from smart_home import set_lock
        msg = _run_async(set_lock(locked))
        return {"success": True, "message": msg}
    except Exception as e:
        return {"success": False, "message": f"Lock set error: {e}"}


def home_sensors() -> dict:
    """Check leak/motion/etc sensor status."""
    try:
        from smart_home import get_sensor_status
        sensors = _run_async(get_sensor_status())
        return {"success": True, "data": sensors}
    except Exception as e:
        return {"success": False, "message": f"Sensor error: {e}"}


def home_schedule_add(name: str, temperature: int, mode: str, time: str, days: str = "daily") -> dict:
    """Create a recurring thermostat schedule.

    Args:
        name: Schedule name (e.g. "Nightly", "Weekday Morning").
        temperature: Target temp in F.
        mode: 'cool', 'heat', 'auto'.
        time: Time like "10:00 PM" or "22:00".
        days: "daily", "weekdays", "weekends", or comma-separated days
              (e.g. "monday,tuesday").
    """
    try:
        from schedules import add_schedule
        msg = add_schedule(name, temperature, mode, time, days)
        return {"success": True, "message": msg}
    except Exception as e:
        return {"success": False, "message": f"Schedule add error: {e}"}


def home_schedule_list() -> dict:
    """List all thermostat schedules."""
    try:
        from schedules import list_schedules
        return {"success": True, "message": list_schedules()}
    except Exception as e:
        return {"success": False, "message": f"Schedule list error: {e}"}


def home_schedule_delete(name: str) -> dict:
    """Delete a thermostat schedule by name."""
    try:
        from schedules import delete_schedule
        return {"success": True, "message": delete_schedule(name)}
    except Exception as e:
        return {"success": False, "message": f"Schedule delete error: {e}"}


# ---------- TOOL REGISTRY ----------
# OpenAI-format function schemas that the LLM can call

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "car_command",
            "description": "Send a direct command to the Genesis GV70. Use car_auto_start instead if the user just says 'start the car' without specifying climate preset.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "enum": ["start", "start-winter", "start-summer", "stop", "lock", "unlock", "status"],
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "car_auto_start",
            "description": "Start the Genesis GV70 with climate preset auto-selected based on current outside temperature.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "health_briefing",
            "description": "Generate a daily or weekly health briefing with insights from Oura and Whoop data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "weekly": {"type": "boolean", "description": "Whether to generate a weekly deep-dive (default: False, i.e. daily)."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "health_ask",
            "description": "Ask a question about the user's health data (Oura, Whoop, workouts). Use this for ANY question about sleep, recovery, HRV, strain, workouts, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "The full question to ask about the user's health."},
                },
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "health_pull_now",
            "description": "Force-pull the latest Oura and Whoop data from their APIs (useful if data seems stale).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "home_thermostat_status",
            "description": "Get current indoor temperature, humidity, thermostat mode, and setpoint.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "home_thermostat_set",
            "description": "Set the thermostat to a specific temperature and mode right now (not a schedule).",
            "parameters": {
                "type": "object",
                "properties": {
                    "temperature": {"type": "integer", "description": "Target temperature in °F (60-85)."},
                    "mode": {"type": "string", "enum": ["cool", "heat", "auto", "off"]},
                },
                "required": ["temperature", "mode"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "home_lock_status",
            "description": "Check whether the front door is locked.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "home_lock_set",
            "description": "Lock or unlock the front door. Execute immediately when requested — no confirmation needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "locked": {"type": "boolean", "description": "True to lock, False to unlock."},
                },
                "required": ["locked"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "home_sensors",
            "description": "Check status of leak/motion/etc sensors.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "home_schedule_add",
            "description": "Create a recurring thermostat schedule. Use this when the user says 'every', 'daily', 'nightly', 'weekdays', 'weekends', etc. For complex requests like 'X at 8am on weekdays, Y at 9am on weekends', call this tool MULTIPLE times (once per schedule).",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "A short descriptive name (e.g. 'Nightly', 'Weekday Morning', 'Weekend Morning')."},
                    "temperature": {"type": "integer"},
                    "mode": {"type": "string", "enum": ["cool", "heat", "auto"]},
                    "time": {"type": "string", "description": "Time like '10:00 PM' or '7:00 AM'."},
                    "days": {"type": "string", "description": "'daily', 'weekdays', 'weekends', or comma-separated like 'monday,wednesday,friday'. Defaults to 'daily'."},
                },
                "required": ["name", "temperature", "mode", "time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "home_schedule_list",
            "description": "List all active thermostat schedules.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "home_schedule_delete",
            "description": "Delete a thermostat schedule by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                },
                "required": ["name"],
            },
        },
    },
]


# Name → function mapping for dispatch
TOOL_HANDLERS = {
    "car_command": car_command,
    "car_auto_start": car_auto_start,
    "health_briefing": health_briefing,
    "health_ask": health_ask,
    "health_pull_now": health_pull_now,
    "home_thermostat_status": home_thermostat_status,
    "home_thermostat_set": home_thermostat_set,
    "home_lock_status": home_lock_status,
    "home_lock_set": home_lock_set,
    "home_sensors": home_sensors,
    "home_schedule_add": home_schedule_add,
    "home_schedule_list": home_schedule_list,
    "home_schedule_delete": home_schedule_delete,
}


def call_tool(name: str, args: dict) -> dict:
    """Dispatch a tool call to its handler."""
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return {"success": False, "message": f"Unknown tool: {name}"}
    try:
        return handler(**args)
    except TypeError as e:
        return {"success": False, "message": f"Bad arguments for {name}: {e}"}
    except Exception as e:
        logger.exception("Tool %s failed", name)
        return {"success": False, "message": f"{name} failed: {e}"}
