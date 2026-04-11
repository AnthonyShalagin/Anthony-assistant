"""Genesis Remote Telegram Bot.

Text commands to control your Genesis GV70 via Telegram.
"""

import logging
import time
from typing import Optional

import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from genesis_api import send_command, VALID_COMMANDS
from weather import auto_detect_command, get_current_temp, COLD_THRESHOLD, HOT_THRESHOLD

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Command aliases — natural language → API command
ALIASES = {
    # Start
    "start": "auto",  # auto-detect
    "start car": "auto",
    "start my car": "auto",
    "remote start": "auto",
    "turn on": "auto",
    "turn on car": "auto",
    "warm up": "start-winter",
    "warm up car": "start-winter",
    "cool down": "start-summer",
    "cool down car": "start-summer",
    "winter": "start-winter",
    "winter start": "start-winter",
    "start winter": "start-winter",
    "summer": "start-summer",
    "summer start": "start-summer",
    "start summer": "start-summer",
    "preset": "start-preset",
    "start preset": "start-preset",
    # Stop
    "stop": "stop",
    "stop car": "stop",
    "turn off": "stop",
    "turn off car": "stop",
    "engine off": "stop",
    # Lock
    "lock": "lock",
    "lock car": "lock",
    "lock doors": "lock",
    "lock it": "lock",
    # Unlock
    "unlock": "unlock",
    "unlock car": "unlock",
    "unlock doors": "unlock",
    "unlock it": "unlock",
    "open": "unlock",
    # Status
    "status": "status",
    "car status": "status",
    "check": "status",
    "check car": "status",
}

# Emoji for each command type
EMOJI = {
    "start": "🚗",
    "start-winter": "❄️",
    "start-summer": "☀️",
    "start-preset": "🔧",
    "stop": "🛑",
    "lock": "🔒",
    "unlock": "🔓",
    "status": "📊",
}

# Human-readable labels
LABELS = {
    "start": "Starting (72°F)",
    "start-winter": "Starting — Winter (80°F, heated seats, defrost)",
    "start-summer": "Starting — Summer (65°F, ventilated seats)",
    "start-preset": "Starting — Preset",
    "stop": "Stopping engine",
    "lock": "Locking doors",
    "unlock": "Unlocking doors",
    "status": "Checking status",
}


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
    """Process an incoming message and execute the command."""
    text = text.strip().lower()

    # Help
    if text in ("/help", "help", "/start"):
        send_message(
            "🚗 Genesis Remote\n\n"
            "Commands:\n"
            "• start — auto-detects winter/summer\n"
            "• start winter — heated seats + defrost\n"
            "• start summer — cooled seats\n"
            "• stop — turn off engine\n"
            "• lock / unlock\n"
            "• status — check vehicle\n\n"
            "Just text naturally — 'start my car', 'lock it', etc.",
            chat_id,
        )
        return

    # Strip leading slash if present
    if text.startswith("/"):
        text = text[1:]

    # Match to command
    command = ALIASES.get(text)

    if command is None:
        # Try partial matching
        for alias, cmd in ALIASES.items():
            if alias in text:
                command = cmd
                break

    if command is None:
        send_message("❓ Didn't catch that. Text 'help' for commands.", chat_id)
        return

    # Handle auto-detect
    if command == "auto":
        command = auto_detect_command()
        temp = get_current_temp()
        temp_note = f" (currently {temp:.0f}°F)" if temp else ""
        emoji = EMOJI.get(command, "🚗")
        label = LABELS.get(command, command)
        send_message(f"{emoji} {label}{temp_note}...", chat_id)
    else:
        emoji = EMOJI.get(command, "🚗")
        label = LABELS.get(command, command)
        send_message(f"{emoji} {label}...", chat_id)

    # Execute command
    result = send_command(command)

    if result["success"]:
        send_message(f"✅ Done — {result['message']}", chat_id)
    else:
        send_message(f"❌ Failed — {result['message']}", chat_id)


def poll_loop() -> None:
    """Run the Telegram polling loop."""
    logger.info("Genesis Remote bot starting...")
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
