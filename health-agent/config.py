"""Configuration loaded from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Database
DB_PATH = os.environ.get("DB_PATH", str(DATA_DIR / "health.db"))

# Telegram
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# Oura Ring — bearer token auth
OURA_TOKEN = os.environ.get("OURA_TOKEN", "")

# Whoop — OAuth2
WHOOP_CLIENT_ID = os.environ.get("WHOOP_CLIENT_ID", "")
WHOOP_CLIENT_SECRET = os.environ.get("WHOOP_CLIENT_SECRET", "")
WHOOP_REDIRECT_URI = os.environ.get("WHOOP_REDIRECT_URI", "https://localhost/callback")

# LLM via OpenRouter
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "anthropic/claude-sonnet-4-6")

# Schedule (24-hour format, Eastern Time)
SCHEDULE = {
    "healthcheck": "09:00",
    "oura_pull": "09:30",
    "whoop_pull": "09:35",
    "daily_briefing": "10:00",
    "weekly_briefing": "10:30",  # Sundays only
}
