"""Client for the Genesis Vercel API."""

import logging
from typing import Optional

import requests

from config import GENESIS_API_URL, GENESIS_API_KEY, GENESIS_PIN

logger = logging.getLogger(__name__)

VALID_COMMANDS = {
    "start", "start-winter", "start-summer", "start-preset",
    "stop", "lock", "unlock", "status",
}


def send_command(command: str) -> dict:
    """Send a command to the Genesis Vercel API.

    Returns dict with 'success' and 'message' keys.
    """
    if command not in VALID_COMMANDS:
        return {"success": False, "message": f"Unknown command: {command}"}

    try:
        resp = requests.post(
            f"{GENESIS_API_URL}/api/command",
            headers={
                "X-API-Key": GENESIS_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "command": command,
                "pin": GENESIS_PIN,
            },
            timeout=120,  # Genesis commands can take a while
        )

        if resp.ok:
            data = resp.json()
            return {"success": True, "message": data.get("message", "Command sent")}
        else:
            return {
                "success": False,
                "message": f"API error {resp.status_code}: {resp.text[:200]}",
            }

    except requests.Timeout:
        return {"success": False, "message": "Command timed out — Genesis may still be processing"}
    except requests.RequestException as e:
        logger.error("Genesis API call failed: %s", e)
        return {"success": False, "message": f"Connection error: {e}"}
