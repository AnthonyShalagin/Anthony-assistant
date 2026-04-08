"""Main entry point for the Hermes Health Agent.

Initializes the database, starts the scheduler, and runs
the Telegram polling loop.
"""

import logging
import sys
import threading

from config import DB_PATH, TELEGRAM_BOT_TOKEN
from database import init_db
from scheduler import create_default_scheduler
from telegram_bot import poll_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Start the health agent."""
    logger.info("🏥 Hermes Health Agent starting...")

    # Initialize database
    init_db()
    logger.info("Database initialized at %s", DB_PATH)

    # Start scheduler (background thread)
    scheduler = create_default_scheduler()
    scheduler.start(background=True)
    logger.info("Scheduler running with %d jobs", len(scheduler.jobs))

    # Start Telegram polling (foreground / blocking)
    if TELEGRAM_BOT_TOKEN:
        logger.info("Starting Telegram bot polling...")
        try:
            poll_loop()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            scheduler.stop()
    else:
        logger.warning("TELEGRAM_BOT_TOKEN not set — running scheduler only")
        try:
            # Keep main thread alive
            scheduler._thread.join()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            scheduler.stop()


if __name__ == "__main__":
    main()
