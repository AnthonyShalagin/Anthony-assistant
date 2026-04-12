"""Configuration for Jarvis master orchestrator bot."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Telegram
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# LLM
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "anthropic/claude-sonnet-4-6")

# Internal service paths (for reusing existing bot code)
# All three bots live in sibling directories under Anthony-assistant/
HEALTH_AGENT_DIR = BASE_DIR.parent / "health-agent"
GENESIS_BOT_DIR = BASE_DIR.parent / "genesis-bot"
HOME_BOT_DIR = BASE_DIR.parent / "home-bot"

# Genesis local service (Node.js bluelinky)
GENESIS_SERVICE_URL = "http://127.0.0.1:3100"

# Health database path (reuse existing)
HEALTH_DB_PATH = str(HEALTH_AGENT_DIR / "data" / "health.db")

# Weather
ZIP_CODE = os.environ.get("ZIP_CODE", "07311")
