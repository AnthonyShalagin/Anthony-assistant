"""Jarvis — master orchestrator Telegram bot.

One unified assistant that routes messages across car, home, and
health domains using an LLM with function calling.
"""

import json
import logging
import time
from collections import defaultdict
from typing import Optional

import requests

from auth import is_authorized
from config import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
    OPENROUTER_API_KEY, LLM_MODEL,
)
from tools import TOOL_SCHEMAS, call_tool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Per-user conversation history (kept in memory — resets on restart)
_history: dict[str, list[dict]] = defaultdict(list)
MAX_HISTORY_TURNS = 10  # Keep last 10 user+assistant exchanges

SYSTEM_PROMPT = """You are Jarvis, a personal assistant for Anthony. You help with his car (Genesis GV70), home (SmartRent thermostat + Yale lock + sensors), and health (Oura, Whoop, workouts).

Available domains and tools:
- CAR: Use car_auto_start for "start the car" (picks winter/summer based on temp). Use car_command for specific commands (stop, lock, unlock, status, or explicit winter/summer starts).
- HOME: Thermostat (status/set/schedule), front door lock, sensors. For "set temp to X every Y" use home_schedule_add. For "set temp to X" (no recurrence) use home_thermostat_set.
- HEALTH: Use health_ask for ANY question about sleep/recovery/HRV/strain/workouts. Use health_briefing only when asked for a briefing or summary.

Critical rules:
1. Execute lock/unlock commands immediately — no confirmation needed.
2. Be concise. Reply in 1-3 sentences. No fluff.
3. Don't restate numbers the user can see in their apps.
4. If multiple actions are requested ("start car and lock door"), call both tools in parallel.
5. If a tool fails, tell the user what went wrong in plain English.
6. For day-specific schedules ("weekdays", "weekends"), use the days parameter. For requests with multiple schedules, call home_schedule_add multiple times."""


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


def _call_llm(messages: list[dict]) -> dict:
    """Call OpenRouter with tool calling enabled."""
    resp = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": LLM_MODEL,
            "messages": messages,
            "tools": TOOL_SCHEMAS,
            "max_tokens": 800,
            "temperature": 0.3,
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


def handle_message(text: str, chat_id: str) -> None:
    """Process an incoming message through the LLM orchestrator."""
    if not is_authorized(chat_id):
        return

    text = text.strip()
    if not text:
        return

    # Built-in commands
    if text.lower() in ("/help", "/start", "help"):
        send_message(
            "🎩 Jarvis at your service.\n\n"
            "Just text naturally:\n"
            "• start the car, lock the door\n"
            "• set temp to 68 every night at 10pm\n"
            "• how's my recovery trending?\n"
            "• any leaks detected?\n"
            "\n/reset — clear conversation memory",
            chat_id,
        )
        return

    if text.lower() in ("/reset", "reset", "start over"):
        _history[chat_id].clear()
        send_message("🔄 Memory cleared.", chat_id)
        return

    # Build message history
    history = _history[chat_id]
    history.append({"role": "user", "content": text})

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    try:
        # Tool-calling loop
        for iteration in range(5):  # Max 5 tool-calling rounds
            response = _call_llm(messages)
            choice = response["choices"][0]
            msg = choice["message"]
            tool_calls = msg.get("tool_calls")

            if not tool_calls:
                # Final answer
                content = msg.get("content", "").strip()
                if content:
                    history.append({"role": "assistant", "content": content})
                    send_message(content, chat_id)
                break

            # Execute tools
            assistant_msg = {"role": "assistant", "content": msg.get("content") or "", "tool_calls": tool_calls}
            messages.append(assistant_msg)
            history.append(assistant_msg)

            for tc in tool_calls:
                fn_name = tc["function"]["name"]
                try:
                    fn_args = json.loads(tc["function"]["arguments"] or "{}")
                except json.JSONDecodeError:
                    fn_args = {}

                logger.info("Tool call: %s(%s)", fn_name, fn_args)
                result = call_tool(fn_name, fn_args)
                result_str = json.dumps(result)

                tool_msg = {
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result_str,
                }
                messages.append(tool_msg)
                history.append(tool_msg)

        # Trim history to last N turns to keep context size bounded
        _trim_history(chat_id)

    except requests.RequestException as e:
        logger.error("LLM call failed: %s", e)
        send_message(f"❌ LLM error: {e}", chat_id)
    except Exception as e:
        logger.exception("Unexpected error")
        send_message(f"❌ Something broke: {e}", chat_id)


def _trim_history(chat_id: str) -> None:
    """Keep only the last MAX_HISTORY_TURNS user+assistant exchanges."""
    history = _history[chat_id]
    # Count user messages; each one is a "turn"
    user_idx = [i for i, m in enumerate(history) if m.get("role") == "user"]
    if len(user_idx) > MAX_HISTORY_TURNS:
        cutoff = user_idx[-MAX_HISTORY_TURNS]
        _history[chat_id] = history[cutoff:]


def poll_loop() -> None:
    logger.info("Jarvis starting...")
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
