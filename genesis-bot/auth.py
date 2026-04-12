"""Shared authorization helper for all bots.

Whitelist-based access control — only specified Telegram chat IDs
can interact with the bot. All other messages are silently logged
and ignored.
"""

import logging
import os
from typing import Set

logger = logging.getLogger(__name__)


def _load_allowed_users() -> Set[str]:
    """Load allowed chat IDs from ALLOWED_CHAT_IDS env var (comma-separated)."""
    raw = os.environ.get("ALLOWED_CHAT_IDS", "").strip()
    if not raw:
        return set()
    return {uid.strip() for uid in raw.split(",") if uid.strip()}


def is_authorized(chat_id: str) -> bool:
    """Check if a chat_id is on the whitelist."""
    allowed = _load_allowed_users()
    if not allowed:
        logger.warning("No ALLOWED_CHAT_IDS configured — denying all")
        return False
    authorized = str(chat_id) in allowed
    if not authorized:
        logger.warning("Unauthorized access attempt from chat_id=%s", chat_id)
    return authorized
