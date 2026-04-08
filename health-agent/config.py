"""Configuration loaded from environment variables."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
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

# Garmin — OAuth 1.0a
GARMIN_CONSUMER_KEY = os.environ.get("GARMIN_CONSUMER_KEY", "")
GARMIN_CONSUMER_SECRET = os.environ.get("GARMIN_CONSUMER_SECRET", "")

# LLM via OpenRouter
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "anthropic/claude-sonnet-4-6")

# Schedule (24-hour format, Eastern Time)
SCHEDULE = {
    "healthcheck": "06:00",
    "oura_pull": "07:00",
    "whoop_pull": "07:05",
    "garmin_pull": "07:10",
    "daily_briefing": "07:30",
    "weekly_briefing": "09:00",  # Sundays only
}
