"""Configuration for Home Control Telegram Bot."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Telegram
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# SmartRent
SMARTRENT_EMAIL = os.environ.get("SMARTRENT_EMAIL", "")
SMARTRENT_PASSWORD = os.environ.get("SMARTRENT_PASSWORD", "")

# Database for schedules
DB_PATH = str(BASE_DIR / "data" / "schedules.db")
