"""Configuration for Genesis Remote Telegram Bot."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Telegram
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# Genesis Vercel API
GENESIS_API_URL = os.environ.get("GENESIS_API_URL", "https://genesis-sms.vercel.app")
GENESIS_API_KEY = os.environ.get("GENESIS_API_KEY", "")
GENESIS_PIN = os.environ.get("GENESIS_PIN", "")

# Weather (for auto-detection)
ZIP_CODE = os.environ.get("ZIP_CODE", "07311")
