"""Telegram bot for receiving Strong CSV uploads, sending briefings,
and interactive health Q&A.

Uses long-polling (no webhook / no exposed ports).
"""

import logging
import time
from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

import requests

from auth import is_authorized
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, LLM_MODEL, OPENROUTER_API_KEY
from parsers.strong import parse_csv

logger = logging.getLogger(__name__)

BASE_URL = "https://api.telegram.org/bot{token}"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

CHAT_SYSTEM_PROMPT = """You are a world-class functional medicine practitioner and health coach. You have access to this person's real health data from Oura Ring, Whoop, and their workout history from the Strong app.

When they ask you a question, answer based on their ACTUAL data provided below. Be specific — reference their real numbers, trends, and workout history. Don't give generic health advice.

Rules:
- Be concise and direct. 2-5 sentences unless they ask for detail.
- Reference their specific data points when relevant
- If the data doesn't contain what they're asking about, say so
- Think like a practitioner reviewing a patient's chart, not a chatbot
- No disclaimers about not being a doctor — they know that"""


def _url(method: str, token: Optional[str] = None) -> str:
    return f"{BASE_URL.format(token=token or TELEGRAM_BOT_TOKEN)}/{method}"


def send_message(
    text: str,
    chat_id: Optional[str] = None,
    token: Optional[str] = None,
    parse_mode: str = "HTML",
) -> dict:
    """Send a message via Telegram."""
    cid = chat_id or TELEGRAM_CHAT_ID
    if not cid or not (token or TELEGRAM_BOT_TOKEN):
        logger.warning("Telegram not configured — message not sent")
        return {}

    messages = _split_message(text, 4096)
    result = {}
    for msg in messages:
        resp = requests.post(
            _url("sendMessage", token),
            json={"chat_id": cid, "text": msg, "parse_mode": parse_mode},
            timeout=30,
        )
        if resp.ok:
            result = resp.json()
        else:
            logger.error("Telegram send failed: %s %s", resp.status_code, resp.text)
    return result


def _split_message(text: str, max_len: int) -> list[str]:
    """Split a message into chunks that fit Telegram's limit."""
    if len(text) <= max_len:
        return [text]
    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        split_at = text.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = max_len
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks


def get_updates(offset: int = 0, timeout: int = 30, token: Optional[str] = None) -> list[dict]:
    """Long-poll for updates from Telegram."""
    try:
        resp = requests.get(
            _url("getUpdates", token),
            params={"offset": offset, "timeout": timeout},
            timeout=timeout + 10,
        )
        resp.raise_for_status()
        return resp.json().get("result", [])
    except requests.RequestException as e:
        logger.error("Failed to get Telegram updates: %s", e)
        return []


def download_file(file_id: str, token: Optional[str] = None) -> Optional[str]:
    """Download a file from Telegram and return its content as string."""
    try:
        resp = requests.get(
            _url("getFile", token),
            params={"file_id": file_id},
            timeout=15,
        )
        resp.raise_for_status()
        file_path = resp.json()["result"]["file_path"]

        t = token or TELEGRAM_BOT_TOKEN
        download_url = f"https://api.telegram.org/file/bot{t}/{file_path}"
        content_resp = requests.get(download_url, timeout=30)
        content_resp.raise_for_status()
        return content_resp.text
    except Exception as e:
        logger.error("Failed to download Telegram file: %s", e)
        return None


def _build_health_context(db_path: Optional[str] = None) -> str:
    """Build a comprehensive health data snapshot for Q&A."""
    from database import get_db, get_metrics, get_recent_workouts, get_metric_average

    parts = []
    today = date.today()
    db_kwargs = {"db_path": db_path} if db_path else {}

    with get_db(**db_kwargs) as conn:
        # Recent health metrics (14 days)
        metrics = get_metrics(conn, days=14)
        if metrics:
            parts.append("=== HEALTH METRICS (last 14 days) ===")
            by_date = defaultdict(list)
            for m in metrics:
                by_date[m["date"]].append(m)
            for dt in sorted(by_date.keys(), reverse=True)[:7]:
                day_metrics = by_date[dt]
                line = f"  {dt}: "
                items = []
                for m in day_metrics:
                    if m["value"] is not None:
                        items.append(f"{m['metric_name']}={m['value']:.0f}")
                line += ", ".join(items[:8])
                parts.append(line)
            parts.append("")

            # Averages
            parts.append("=== AVERAGES ===")
            for source in ["oura", "whoop"]:
                for metric in get_metrics(conn, source=source, days=1):
                    name = metric["metric_name"]
                    avg7 = get_metric_average(conn, source, name, 7)
                    avg30 = get_metric_average(conn, source, name, 30)
                    if avg7 is not None:
                        line = f"  {name} ({source}): 7d avg={avg7:.1f}"
                        if avg30 is not None:
                            line += f", 30d avg={avg30:.1f}"
                        parts.append(line)
            parts.append("")

        # Workouts (last 30 days)
        workouts = get_recent_workouts(conn, days=30)
        if workouts:
            parts.append("=== WORKOUT HISTORY (last 30 days) ===")
            by_workout = defaultdict(list)
            for w in workouts:
                by_workout[(w["date"], w["workout_name"])].append(w)

            workout_dates = sorted(set(w["date"] for w in workouts))
            parts.append(f"Sessions: {len(workout_dates)} in last 30 days")

            # Exercise frequency and bests
            exercise_sets = defaultdict(int)
            exercise_best_weight = defaultdict(float)
            exercise_best_1rm = defaultdict(float)

            for (dt, name), sets in by_workout.items():
                for s in sets:
                    ex = s["exercise"]
                    exercise_sets[ex] += 1
                    if s["weight"] and s["weight"] > exercise_best_weight[ex]:
                        exercise_best_weight[ex] = s["weight"]
                    if s["estimated_1rm"] and s["estimated_1rm"] > exercise_best_1rm[ex]:
                        exercise_best_1rm[ex] = s["estimated_1rm"]

            # Top exercises
            top = sorted(exercise_sets.items(), key=lambda x: -x[1])[:15]
            for ex, count in top:
                line = f"  {ex}: {count} sets"
                if exercise_best_weight[ex] > 0:
                    line += f", best weight: {exercise_best_weight[ex]:.0f}lb"
                if exercise_best_1rm[ex] > 0:
                    line += f", est 1RM: {exercise_best_1rm[ex]:.0f}lb"
                parts.append(line)
            parts.append("")

            # Last 5 sessions
            parts.append("=== RECENT SESSIONS ===")
            recent = sorted(by_workout.items(), key=lambda x: x[0])[-5:]
            for (dt, name), sets in recent:
                exercises = sorted(set(s["exercise"] for s in sets))
                total_vol = sum(s["volume"] for s in sets if s["volume"])
                parts.append(f"  {dt} — {name}: {', '.join(exercises)} | vol: {total_vol:.0f}")

    return "\n".join(parts)


def handle_question(question: str, db_path: Optional[str] = None) -> str:
    """Answer a health question using the user's actual data."""
    context = _build_health_context(db_path)

    full_prompt = f"Here is the user's current health data:\n\n{context}\n\nUser question: {question}"

    if not OPENROUTER_API_KEY:
        return "LLM not configured — can't answer questions yet."

    try:
        resp = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": CHAT_SYSTEM_PROMPT},
                    {"role": "user", "content": full_prompt},
                ],
                "max_tokens": 500,
                "temperature": 0.3,
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error("Q&A LLM call failed: %s", e)
        return f"Sorry, couldn't process that — {e}"


def handle_document(update: dict, db_path: Optional[str] = None, token: Optional[str] = None) -> Optional[str]:
    """Handle a document upload — parse Strong CSV if applicable."""
    message = update.get("message", {})
    doc = message.get("document")
    chat_id = str(message.get("chat", {}).get("id", ""))

    # Security: deny unauthorized users
    if not is_authorized(chat_id):
        return None

    if not doc:
        return None

    file_name = doc.get("file_name", "")
    if not file_name.lower().endswith(".csv"):
        send_message("⚠️ Please upload a .csv file from the Strong app.", chat_id, token)
        return None

    content = download_file(doc["file_id"], token)
    if not content:
        send_message("❌ Failed to download file.", chat_id, token)
        return None

    try:
        summary = parse_csv(content, db_path)
        working_sets = summary['sets'] - summary.get('warmup_sets', 0)
        msg = (
            f"💪 Workout imported!\n"
            f"• {working_sets} working sets + {summary.get('warmup_sets', 0)} warmup across {summary['exercises']} exercises\n"
            f"• {summary['workouts']} workout session(s)\n"
        )
        if summary.get("exercise_list"):
            msg += f"• Exercises: {', '.join(summary['exercise_list'][:10])}"
            if len(summary['exercise_list']) > 10:
                msg += f" (+{len(summary['exercise_list']) - 10} more)"
        send_message(msg, chat_id, token)
        return msg
    except ValueError as e:
        send_message(f"❌ CSV parse error: {e}", chat_id, token)
        return None
    except Exception as e:
        logger.error("Unexpected error parsing CSV: %s", e)
        send_message("❌ Unexpected error processing workout file.", chat_id, token)
        return None


def poll_loop(db_path: Optional[str] = None, token: Optional[str] = None) -> None:
    """Run the Telegram polling loop (blocking)."""
    logger.info("Starting Telegram polling loop")
    offset = 0

    while True:
        updates = get_updates(offset, token=token)
        for update in updates:
            offset = update["update_id"] + 1

            # Handle document uploads
            if "message" in update and "document" in update["message"]:
                handle_document(update, db_path, token)
            elif "message" in update and "text" in update["message"]:
                text = update["message"]["text"].strip()
                chat_id = str(update["message"]["chat"]["id"])

                # Security: deny unauthorized users silently
                if not is_authorized(chat_id):
                    continue

                if text == "/status":
                    send_message("✅ Hermes Health Agent is running.", chat_id, token)
                elif text == "/briefing":
                    from briefing.generator import generate_briefing
                    result = generate_briefing(db_path=db_path)
                    send_message(result["full_message"], chat_id, token)
                elif text.startswith("/"):
                    # Ignore unknown commands
                    pass
                else:
                    # Conversational Q&A — answer any text message
                    answer = handle_question(text, db_path)
                    send_message(answer, chat_id, token)

        time.sleep(1)
