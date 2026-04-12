"""Home Control Telegram Bot.

Controls SmartRent thermostat, lock, and sensors via Telegram.
"""

import logging
import re
import time
import threading
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from smart_home import (
    get_thermostat_status, set_thermostat,
    get_lock_status, set_lock,
    get_sensor_status, run_async,
)
from schedules import init_db, add_schedule, delete_schedule, list_schedules, get_due_schedules

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")
BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Pending confirmations: chat_id -> {"action": ..., "expires": ...}
_pending = {}


def send_message(text: str, chat_id: Optional[str] = None) -> dict:
    """Send a Telegram message."""
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


def handle_message(text: str, chat_id: str) -> None:
    """Process an incoming message."""
    text_lower = text.strip().lower()

    # Check for pending confirmation
    if chat_id in _pending:
        pending = _pending.pop(chat_id)
        if time.time() > pending["expires"]:
            send_message("Confirmation expired. Try again.", chat_id)
            return
        if text_lower in ("yes", "y", "confirm", "do it"):
            action = pending["action"]
            action_type = pending["type"]
            if action_type == "lock":
                result = run_async(set_lock(True))
                send_message(f"🔒 {result}", chat_id)
            elif action_type == "unlock":
                result = run_async(set_lock(False))
                send_message(f"🔓 {result}", chat_id)
            return
        else:
            send_message("Cancelled.", chat_id)
            return

    # Help
    if text_lower in ("/help", "help", "/start"):
        send_message(
            "🏠 Home Control\n\n"
            "Thermostat:\n"
            "• what's the temperature?\n"
            "• set it to 70 cooling\n"
            "• turn off thermostat\n\n"
            "Lock:\n"
            "• lock the door\n"
            "• unlock the door\n"
            "• is the door locked?\n\n"
            "Sensors:\n"
            "• check sensors\n\n"
            "Schedules:\n"
            "• set temp to 68 every night at 10pm\n"
            "• show my schedules\n"
            "• delete <name> schedule",
            chat_id,
        )
        return

    # --- Thermostat commands ---

    # Get temperature
    if any(kw in text_lower for kw in ["temperature", "temp?", "how warm", "how cold", "thermostat status", "what's the temp"]):
        status = run_async(get_thermostat_status())
        if "error" in status:
            send_message(f"❌ {status['error']}", chat_id)
            return
        mode = status["mode"] or "off"
        setpoint = status["cooling_setpoint"] if mode == "cool" else status["heating_setpoint"]
        msg = f"🌡️ It's {status['current_temp']}°F inside"
        if status.get("current_humidity"):
            msg += f" with {status['current_humidity']}% humidity"
        msg += f". Thermostat is {mode}"
        if mode != "off" and setpoint:
            msg += f", set to {setpoint}°F"
        msg += "."
        send_message(msg, chat_id)
        return

    # Set temperature: "set to 70 cooling" / "set temp to 68" / "70 degrees"
    temp_match = re.search(
        r'(?:set|change|make|put)?\s*(?:it|temp|thermostat|temperature)?\s*(?:to)?\s*(\d{2})\s*°?\s*(?:degrees?)?\s*(cool(?:ing)?|heat(?:ing)?|auto|off)?',
        text_lower,
    )
    if not temp_match:
        # Try simple "70 cooling" or "70 degrees"
        temp_match = re.search(r'(\d{2})\s*°?\s*(?:degrees?)?\s*(cool(?:ing)?|heat(?:ing)?|auto|off)?', text_lower)

    if temp_match and 60 <= int(temp_match.group(1)) <= 85:
        temp = int(temp_match.group(1))
        mode = temp_match.group(2) or "cool"
        if mode.startswith("cool"):
            mode = "cool"
        elif mode.startswith("heat"):
            mode = "heat"
        result = run_async(set_thermostat(temp, mode))
        send_message(f"✅ {result}", chat_id)
        return

    # Turn off thermostat
    if any(kw in text_lower for kw in ["turn off thermostat", "thermostat off", "hvac off", "ac off"]):
        result = run_async(set_thermostat(72, "off"))
        send_message(f"✅ {result}", chat_id)
        return

    # --- Lock commands ---

    # Check lock status
    if any(kw in text_lower for kw in ["is the door", "door locked", "lock status", "is it locked", "check lock", "door status"]):
        status = run_async(get_lock_status())
        if "error" in status:
            send_message(f"❌ {status['error']}", chat_id)
            return
        state = "locked 🔒" if status["locked"] else "unlocked 🔓"
        send_message(f"{status['name']} is {state}.", chat_id)
        return

    # Lock door
    if any(kw in text_lower for kw in ["lock the", "lock door", "lock it", "lock up"]) and "unlock" not in text_lower:
        _pending[chat_id] = {
            "type": "lock",
            "action": "lock",
            "expires": time.time() + 30,
        }
        send_message("🔒 Are you sure you want to lock the door?", chat_id)
        return

    # Unlock door
    if any(kw in text_lower for kw in ["unlock the", "unlock door", "unlock it", "open the door", "open door"]):
        _pending[chat_id] = {
            "type": "unlock",
            "action": "unlock",
            "expires": time.time() + 30,
        }
        send_message("🔓 Are you sure you want to unlock the door?", chat_id)
        return

    # --- Sensor commands ---

    if any(kw in text_lower for kw in ["sensor", "leak", "check sensor"]):
        sensors = run_async(get_sensor_status())
        if not sensors:
            send_message("No sensors found.", chat_id)
            return
        lines = ["📡 Sensors:"]
        for s in sensors:
            status = "⚠️ LEAK DETECTED" if s["leak"] else "✅ No leak"
            lines.append(f"  {s['name']}: {status}")
        send_message("\n".join(lines), chat_id)
        return

    # --- Schedule commands ---

    # Show schedules
    if any(kw in text_lower for kw in ["show schedule", "my schedule", "list schedule", "schedules"]):
        send_message(list_schedules(), chat_id)
        return

    # Delete schedule: "delete nightly schedule"
    del_match = re.search(r'(?:delete|remove|cancel)\s+["\']?(\w+)["\']?\s*schedule', text_lower)
    if del_match:
        name = del_match.group(1)
        send_message(delete_schedule(name), chat_id)
        return

    # Create schedule: "set temp to 68 every night at 10pm"
    sched_match = re.search(
        r'(?:set|schedule)\s+(?:temp(?:erature)?\s+(?:to\s+)?)?(\d{2})\s*°?\s*(?:degrees?)?\s*(?:(cool(?:ing)?|heat(?:ing)?)\s+)?(?:every\s+)?(?:night|day|daily)?\s*(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)',
        text_lower,
    )
    if sched_match:
        temp = int(sched_match.group(1))
        mode = sched_match.group(2) or "cool"
        if mode.startswith("cool"):
            mode = "cool"
        elif mode.startswith("heat"):
            mode = "heat"
        raw_time = sched_match.group(3).strip()
        # Normalize time
        if ":" not in raw_time:
            if "pm" in raw_time or "am" in raw_time:
                raw_time = raw_time.replace("pm", ":00 PM").replace("am", ":00 AM")
            else:
                raw_time += ":00"
        time_str = raw_time.upper()

        # Generate a name
        hour = datetime.strptime(time_str.replace(" ", ""), "%I:%M%p").hour if "M" in time_str else int(raw_time.split(":")[0])
        if hour >= 20 or hour <= 4:
            name = "Nightly"
        elif hour >= 5 and hour <= 11:
            name = "Morning"
        elif hour >= 12 and hour <= 16:
            name = "Afternoon"
        else:
            name = "Evening"

        result = add_schedule(name, temp, mode, time_str)
        send_message(f"⏰ {result}", chat_id)
        return

    # Unknown command
    send_message("❓ Didn't catch that. Text 'help' for commands.", chat_id)


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

            # Clean old keys
            if len(last_run) > 100:
                last_run.clear()
        except Exception as e:
            logger.error("Schedule loop error: %s", e)

        time.sleep(30)


def poll_loop() -> None:
    """Run the Telegram polling loop."""
    logger.info("Home Control bot starting...")

    # Initialize schedule database
    init_db()

    # Start schedule checker in background
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
