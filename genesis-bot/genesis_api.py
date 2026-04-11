"""Client for the local Genesis bluelinky service."""

import logging

import requests

logger = logging.getLogger(__name__)

# Local service running on the same server
SERVICE_URL = "http://127.0.0.1:3100"

VALID_COMMANDS = {
    "start", "start-winter", "start-summer", "start-preset",
    "stop", "lock", "unlock", "status",
}


def send_command(command: str) -> dict:
    """Send a command to the local Genesis service.

    Returns dict with 'success' and 'message' keys.
    """
    if command not in VALID_COMMANDS:
        return {"success": False, "message": f"Unknown command: {command}"}

    try:
        resp = requests.post(
            f"{SERVICE_URL}/command",
            json={"command": command},
            timeout=120,  # Genesis commands can take a while
        )

        data = resp.json()
        return {
            "success": data.get("success", False),
            "message": data.get("message", "Unknown response"),
        }

    except requests.Timeout:
        return {"success": False, "message": "Command timed out — Genesis may still be processing"}
    except requests.RequestException as e:
        logger.error("Genesis service call failed: %s", e)
        return {"success": False, "message": f"Service unavailable: {e}"}
