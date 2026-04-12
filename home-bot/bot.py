"""Home Control Telegram Bot — LLM-powered natural language.

Controls SmartRent thermostat, lock, and sensors via Telegram.
Uses Claude (via OpenRouter) with function calling to understand
natural language.
"""

import json
import logging
import os
import threading
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

from auth import is_authorized
from smart_home import (
    get_thermostat_status, set_thermostat,
    get_lock_status, set_lock,
    get_sensor_status, run_async,
)
from schedules import init_db, add_schedule, delete_schedule, list_schedules, get_due_schedules

# Load .env
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "anthropic/claude-sonnet-4-6")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")
BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

_history: dict[str, list[dict]] = defaultdict(list)
MAX_HISTORY_TURNS = 6


SYSTEM_PROMPT = """You are the Home Control assistant — a focused agent for Anthony's apartment. You control:
- Honeywell thermostat (via SmartRent)
- Yale front door lock (via SmartRent)
- Leak sensors (via SmartRent)

Rules:
- Execute lock/unlock commands immediately, no confirmation.
- Be concise: 1-2 sentences.
- For "set temp to X every Y" use schedule_add. For "set temp to X" (now) use thermostat_set.
- For complex requests like "set 72 on weekdays, 68 on weekends" call schedule_add TWICE.
- For day-specific schedules, use the days param: "weekdays", "weekends", "daily", or comma-separated days.
- Don't restate obvious info. Just confirm what you did."""


# ---- Tools ----

def _tool_thermostat_status() -> dict:
    return run_async(get_thermostat_status())

def _tool_thermostat_set(temperature: int, mode: str = "cool") -> dict:
    msg = run_async(set_thermostat(temperature, mode))
    return {"success": True, "message": msg}

def _tool_lock_status() -> dict:
    return run_async(get_lock_status())

def _tool_lock_set(locked: bool) -> dict:
    msg = run_async(set_lock(locked))
    return {"success": True, "message": msg}

def _tool_sensors() -> dict:
    return {"sensors": run_async(get_sensor_status())}

def _tool_schedule_add(name: str, temperature: int, mode: str, time: str, days: str = "daily") -> dict:
    return {"success": True, "message": add_schedule(name, temperature, mode, time, days)}

def _tool_schedule_list() -> dict:
    return {"success": True, "message": list_schedules()}

def _tool_schedule_delete(name: str) -> dict:
    return {"success": True, "message": delete_schedule(name)}


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "thermostat_status",
            "description": "Get current indoor temp, humidity, mode, and setpoint.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "thermostat_set",
            "description": "Set thermostat to a specific temperature NOW (not a recurring schedule).",
            "parameters": {
                "type": "object",
                "properties": {
                    "temperature": {"type": "integer"},
                    "mode": {"type": "string", "enum": ["cool", "heat", "auto", "off"]},
                },
                "required": ["temperature", "mode"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lock_status",
            "description": "Check whether the front door is locked.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lock_set",
            "description": "Lock (true) or unlock (false) the front door immediately.",
            "parameters": {
                "type": "object",
                "properties": {"locked": {"type": "boolean"}},
                "required": ["locked"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sensors",
            "description": "Check status of leak/motion sensors.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_add",
            "description": "Create a recurring thermostat schedule. For complex requests like 'X on weekdays, Y on weekends', call this MULTIPLE times.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Short name (e.g. 'Weekday Morning', 'Nightly')."},
                    "temperature": {"type": "integer"},
                    "mode": {"type": "string", "enum": ["cool", "heat", "auto"]},
                    "time": {"type": "string", "description": "Time like '10:00 PM' or '8:00 AM'."},
                    "days": {"type": "string", "description": "'daily', 'weekdays', 'weekends', or comma-separated days. Defaults to 'daily'."},
                },
                "required": ["name", "temperature", "mode", "time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_list",
            "description": "List all thermostat schedules.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_delete",
            "description": "Delete a schedule by name.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        },
    },
]

TOOL_HANDLERS = {
    "thermostat_status": _tool_thermostat_status,
    "thermostat_set": _tool_thermostat_set,
    "lock_status": _tool_lock_status,
    "lock_set": _tool_lock_set,
    "sensors": _tool_sensors,
    "schedule_add": _tool_schedule_add,
    "schedule_list": _tool_schedule_list,
    "schedule_delete": _tool_schedule_delete,
}


def _call_tool(name: str, args: dict) -> dict:
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return {"success": False, "message": f"Unknown tool: {name}"}
    try:
        return handler(**args)
    except Exception as e:
        logger.exception("Tool %s failed", name)
        return {"success": False, "message": f"{name} failed: {e}"}


# ---- Telegram ----

def send_message(text: str, chat_id: Optional[str] = None) -> dict:
    cid = chat_id or TELEGRAM_CHAT_ID
    try:
        resp = requests.post(
            f"{BASE_URL}/sendMessage",
            json={"chat_id": cid, "text": text},
            timeout=30,
        )
        return resp.json() if resp.ok else {}
    except Exception as e:
        logger.error("Telegram send failed: %s", e)
        return {}


def _llm_call(messages: list[dict]) -> dict:
    resp = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": LLM_MODEL,
            "messages": messages,
            "tools": TOOLS,
            "max_tokens": 600,
            "temperature": 0.3,
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


def handle_message(text: str, chat_id: str) -> None:
    if not is_authorized(chat_id):
        return

    text = text.strip()
    if not text:
        return

    if text.lower() in ("/help", "/start", "help"):
        send_message(
            "🏠 Home Control — I understand natural language.\n\n"
            "Try:\n"
            "• what's the temperature?\n"
            "• set to 68 now\n"
            "• set 72 on weekdays at 8am, 68 on weekends at 9am\n"
            "• lock the front door\n"
            "• any leaks?\n"
            "• show my schedules",
            chat_id,
        )
        return

    if text.lower() in ("/reset", "reset"):
        _history[chat_id].clear()
        send_message("🔄 Memory cleared.", chat_id)
        return

    history = _history[chat_id]
    history.append({"role": "user", "content": text})
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    try:
        for _ in range(5):
            response = _llm_call(messages)
            choice = response["choices"][0]
            msg = choice["message"]
            tool_calls = msg.get("tool_calls")

            if not tool_calls:
                content = msg.get("content", "").strip()
                if content:
                    history.append({"role": "assistant", "content": content})
                    send_message(content, chat_id)
                break

            assistant_msg = {"role": "assistant", "content": msg.get("content") or "", "tool_calls": tool_calls}
            messages.append(assistant_msg)
            history.append(assistant_msg)

            for tc in tool_calls:
                fn_name = tc["function"]["name"]
                try:
                    fn_args = json.loads(tc["function"]["arguments"] or "{}")
                except json.JSONDecodeError:
                    fn_args = {}

                logger.info("Tool: %s(%s)", fn_name, fn_args)
                result = _call_tool(fn_name, fn_args)
                tool_msg = {
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(result),
                }
                messages.append(tool_msg)
                history.append(tool_msg)

        # Trim history
        user_idx = [i for i, m in enumerate(history) if m.get("role") == "user"]
        if len(user_idx) > MAX_HISTORY_TURNS:
            cutoff = user_idx[-MAX_HISTORY_TURNS]
            _history[chat_id] = history[cutoff:]

    except requests.RequestException as e:
        logger.error("LLM call failed: %s", e)
        send_message(f"❌ LLM error: {e}", chat_id)
    except Exception as e:
        logger.exception("Unexpected error")
        send_message(f"❌ {e}", chat_id)


def _schedule_loop():
    """Background thread that checks for due schedules every 30 seconds."""
    last_run = {}
    while True:
        try:
            due = get_due_schedules()
            now_key = datetime.now(ET).strftime("%Y-%m-%d %H:%M")
            for sched in due:
                key = f"{sched['name']}_{now_key}"
                if key not in last_run:
                    last_run[key] = True
                    logger.info("Running schedule: %s", sched["name"])
                    result = run_async(set_thermostat(sched["temperature"], sched["mode"]))
                    send_message(f"⏰ Schedule \"{sched['name']}\": {result}")
            if len(last_run) > 100:
                last_run.clear()
        except Exception as e:
            logger.error("Schedule loop error: %s", e)
        time.sleep(30)


def poll_loop() -> None:
    logger.info("Home Control bot starting (LLM-powered)...")
    init_db()

    sched_thread = threading.Thread(target=_schedule_loop, daemon=True)
    sched_thread.start()

    offset = 0
    while True:
        try:
            resp = requests.get(
                f"{BASE_URL}/getUpdates",
                params={"offset": offset, "timeout": 30},
                timeout=40,
            )
            if not resp.ok:
                logger.error("getUpdates failed: %s", resp.status_code)
                time.sleep(5)
                continue

            updates = resp.json().get("result", [])
            for update in updates:
                offset = update["update_id"] + 1
                message = update.get("message", {})
                text = message.get("text", "")
                chat_id = str(message.get("chat", {}).get("id", ""))
                if text and chat_id:
                    handle_message(text, chat_id)

        except requests.RequestException as e:
            logger.error("Polling error: %s", e)
            time.sleep(5)
        except Exception as e:
            logger.error("Unexpected error: %s", e)
            time.sleep(5)

        time.sleep(1)


if __name__ == "__main__":
    poll_loop()
