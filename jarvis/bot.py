"""Jarvis — master orchestrator Telegram bot.

One unified assistant that routes messages across car, home, and
health domains using an LLM with function calling. Persistent memory
makes it "learn" about the user across restarts.
"""

import json
import logging
import time
from typing import Optional

import requests

from auth import is_authorized
from config import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
    OPENROUTER_API_KEY, LLM_MODEL,
)
import memory
from tools import TOOL_SCHEMAS, call_tool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

HISTORY_WINDOW = 20  # Load last N messages from persistent store per turn
HISTORY_KEEP = 60    # Trim the persistent store to last N per user

BASE_SYSTEM_PROMPT = """You are Jarvis, a personal assistant for Anthony. You help with his car (Genesis GV70), home (SmartRent thermostat + Yale lock + sensors), and health (Oura, Whoop, workouts).

Available domains and tools:
- CAR: Use car_auto_start for "start the car" (auto-picks winter/summer). Use car_command for specific commands (stop, lock, unlock, status, or explicit winter/summer starts).
- HOME: Thermostat status/set, lock status/set, sensors, schedules. For "set temp to X every Y" use home_schedule_add. For "lock the door at Y" use home_lock_schedule_add. For immediate "set temp to X" use home_thermostat_set.
- HEALTH: Use health_ask for ANY question about sleep/recovery/HRV/strain/workouts. Use health_briefing only when asked for a summary.
- MEMORY: Use remember_fact when you learn something lasting about the user (preferences, routines, context worth remembering). Use forget_fact to remove. Use list_facts to see what you know.

Critical rules:
1. Execute lock/unlock commands immediately — no confirmation needed.
2. Be concise. 1-3 sentences. No fluff.
3. Don't restate numbers the user can see in their apps.
4. Multiple actions in one message → call multiple tools.
5. If a tool fails, explain what went wrong plainly.
6. Day-specific schedules use the `days` parameter ('weekdays', 'weekends', 'daily', or comma-separated). Call schedule_add MULTIPLE times for multi-part requests.
7. ACTIVELY remember things about the user — preferences, routines, locations, people they mention, anything that would be useful context later. Call remember_fact to save them."""


def _system_prompt_for(user_id: str) -> str:
    """Compose the system prompt with the user's known facts."""
    base = BASE_SYSTEM_PROMPT
    facts = memory.facts_as_prompt_block(user_id)
    if facts:
        return f"{base}\n\n{facts}"
    return base


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
    if not is_authorized(chat_id):
        return

    text = text.strip()
    if not text:
        return

    # Built-in commands
    if text.lower() in ("/help", "/start", "help"):
        send_message(
            "🎩 Jarvis at your service.\n\n"
            "I remember what you tell me across conversations.\n\n"
            "Try:\n"
            "• start the car, lock the door\n"
            "• set temp to 68 every night at 10pm\n"
            "• lock the door every night at 9pm\n"
            "• how's my recovery trending?\n"
            "• I prefer my coffee at 7am — remember that\n"
            "• what do you know about me?\n\n"
            "/reset — clear recent conversation\n"
            "/forget all — wipe everything I know about you",
            chat_id,
        )
        return

    if text.lower() in ("/reset", "reset"):
        memory.clear_history(chat_id)
        send_message("🔄 Conversation cleared. I still remember your saved preferences though — use /forget all to wipe those too.", chat_id)
        return

    if text.lower() in ("/forget all", "forget all"):
        memory.clear_history(chat_id)
        with memory._conn() as c:
            c.execute("DELETE FROM facts WHERE user_id = ?", (chat_id,))
        send_message("🧹 Everything wiped — I no longer remember anything about you.", chat_id)
        return

    # Persist the user's message
    memory.log_message(chat_id, "user", content=text)

    # Build prompt: system + recent history (from DB)
    history = memory.recent_messages(chat_id, limit=HISTORY_WINDOW)
    messages = [{"role": "system", "content": _system_prompt_for(chat_id)}] + history

    try:
        for _ in range(6):
            response = _call_llm(messages)
            choice = response["choices"][0]
            msg = choice["message"]
            tool_calls = msg.get("tool_calls")

            if not tool_calls:
                content = (msg.get("content") or "").strip()
                if content:
                    memory.log_message(chat_id, "assistant", content=content)
                    send_message(content, chat_id)
                break

            # Execute tools
            assistant_msg = {
                "role": "assistant",
                "content": msg.get("content") or "",
                "tool_calls": tool_calls,
            }
            messages.append(assistant_msg)
            memory.log_message(chat_id, "assistant", content=assistant_msg["content"],
                               tool_calls=tool_calls)

            for tc in tool_calls:
                fn_name = tc["function"]["name"]
                try:
                    fn_args = json.loads(tc["function"]["arguments"] or "{}")
                except json.JSONDecodeError:
                    fn_args = {}

                logger.info("Tool call: %s(%s)", fn_name, fn_args)

                # Inject user_id into memory tools
                if fn_name in ("remember_fact", "forget_fact", "list_facts"):
                    fn_args["_user_id"] = chat_id

                result = call_tool(fn_name, fn_args)
                result_str = json.dumps(result)

                tool_msg = {
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result_str,
                }
                messages.append(tool_msg)
                memory.log_message(chat_id, "tool", content=result_str,
                                   tool_call_id=tc["id"])

        memory.trim_history(chat_id, keep_last=HISTORY_KEEP)

    except requests.RequestException as e:
        logger.error("LLM call failed: %s", e)
        send_message(f"❌ LLM error: {e}", chat_id)
    except Exception as e:
        logger.exception("Unexpected error")
        send_message(f"❌ Something broke: {e}", chat_id)


def poll_loop() -> None:
    logger.info("Jarvis starting (with persistent memory)...")
    memory.init_db()
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
