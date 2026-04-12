"""Configuration for Jarvis master orchestrator bot.

This module also acts as a superset config for sibling bot modules
(health-agent, home-bot, genesis-bot) that import `from config import X`.
We load every sibling .env file and re-export variables so their
modules keep working when imported into Jarvis's process.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
PARENT = BASE_DIR.parent

# Sibling bot dirs
HEALTH_AGENT_DIR = PARENT / "health-agent"
GENESIS_BOT_DIR = PARENT / "genesis-bot"
HOME_BOT_DIR = PARENT / "home-bot"

# Load .env files in order: Jarvis last so it takes precedence for
# shared keys like TELEGRAM_BOT_TOKEN (each bot has its own token
# but when tools run, the Telegram token doesn't matter — they only
# call the underlying services/APIs).
for env_file in (HEALTH_AGENT_DIR / ".env", GENESIS_BOT_DIR / ".env",
                 HOME_BOT_DIR / ".env", BASE_DIR / ".env"):
    if env_file.exists():
        load_dotenv(env_file, override=True)

# --- Jarvis's own config ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# LLM
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "anthropic/claude-sonnet-4-6")

# Weather (genesis-bot/weather.py imports ZIP_CODE)
ZIP_CODE = os.environ.get("ZIP_CODE", "07311")

# --- Sibling exports (so `from config import X` works in their modules) ---

# health-agent database path (health-agent/database.py imports DB_PATH)
DB_PATH = str(HEALTH_AGENT_DIR / "data" / "health.db")
HEALTH_DB_PATH = DB_PATH  # alias for clarity

# health-agent credentials
OURA_TOKEN = os.environ.get("OURA_TOKEN", "")
WHOOP_CLIENT_ID = os.environ.get("WHOOP_CLIENT_ID", "")
WHOOP_CLIENT_SECRET = os.environ.get("WHOOP_CLIENT_SECRET", "")
WHOOP_REDIRECT_URI = os.environ.get("WHOOP_REDIRECT_URI", "https://localhost/callback")
GARMIN_CONSUMER_KEY = os.environ.get("GARMIN_CONSUMER_KEY", "")
GARMIN_CONSUMER_SECRET = os.environ.get("GARMIN_CONSUMER_SECRET", "")

# genesis-bot
GENESIS_API_URL = os.environ.get("GENESIS_API_URL", "https://genesis-sms.vercel.app")
GENESIS_API_KEY = os.environ.get("GENESIS_API_KEY", "")
GENESIS_PIN = os.environ.get("GENESIS_PIN", "")
GENESIS_SERVICE_URL = "http://127.0.0.1:3100"

# Local Genesis Node service (for tools.py)
SMARTRENT_EMAIL = os.environ.get("SMARTRENT_EMAIL", "")
SMARTRENT_PASSWORD = os.environ.get("SMARTRENT_PASSWORD", "")
