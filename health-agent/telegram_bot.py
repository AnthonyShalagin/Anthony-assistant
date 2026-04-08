"""Telegram bot for receiving Strong CSV uploads and sending briefings.

Uses long-polling (no webhook / no exposed ports).
"""

import io
import logging
import time
from typing import Optional

import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from parsers.strong import parse_csv

logger = logging.getLogger(__name__)

BASE_URL = "https://api.telegram.org/bot{token}"


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

    # Telegram has a 4096 char limit; split if needed
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
        # Find a good split point
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
        # Get file path
        resp = requests.get(
            _url("getFile", token),
            params={"file_id": file_id},
            timeout=15,
        )
        resp.raise_for_status()
        file_path = resp.json()["result"]["file_path"]

        # Download content
        t = token or TELEGRAM_BOT_TOKEN
        download_url = f"https://api.telegram.org/file/bot{t}/{file_path}"
        content_resp = requests.get(download_url, timeout=30)
        content_resp.raise_for_status()
        return content_resp.text
    except Exception as e:
        logger.error("Failed to download Telegram file: %s", e)
        return None


def handle_document(update: dict, db_path: Optional[str] = None, token: Optional[str] = None) -> Optional[str]:
    """Handle a document upload — parse Strong CSV if applicable."""
    message = update.get("message", {})
    doc = message.get("document")
    chat_id = str(message.get("chat", {}).get("id", ""))

    if not doc:
        return None

    file_name = doc.get("file_name", "")
    if not file_name.lower().endswith(".csv"):
        send_message("⚠️ Please upload a .csv file from the Strong app.", chat_id, token)
        return None

    # Download and parse
    content = download_file(doc["file_id"], token)
    if not content:
        send_message("❌ Failed to download file.", chat_id, token)
        return None

    try:
        summary = parse_csv(content, db_path)
        msg = (
            f"💪 Workout imported!\n"
            f"• {summary['sets']} sets across {summary['exercises']} exercises\n"
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
                text = update["message"]["text"]
                chat_id = str(update["message"]["chat"]["id"])
                if text == "/status":
                    send_message("✅ Hermes Health Agent is running.", chat_id, token)

        time.sleep(1)
