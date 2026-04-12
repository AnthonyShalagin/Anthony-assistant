"""Chat ID whitelist authorization."""

import logging
import os
from typing import Set

logger = logging.getLogger(__name__)


def _load_allowed_users() -> Set[str]:
    raw = os.environ.get("ALLOWED_CHAT_IDS", "").strip()
    if not raw:
        return set()
    return {uid.strip() for uid in raw.split(",") if uid.strip()}


def is_authorized(chat_id: str) -> bool:
    allowed = _load_allowed_users()
    if not allowed:
        logger.warning("No ALLOWED_CHAT_IDS configured — denying all")
        return False
    ok = str(chat_id) in allowed
    if not ok:
        logger.warning("Unauthorized access attempt from chat_id=%s", chat_id)
    return ok
