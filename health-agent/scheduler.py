"""Cron-based scheduler for daily health data pulls and briefings.

Schedule (Eastern Time):
  06:00 — Healthcheck
  07:00 — Oura daily pull
  07:05 — Whoop daily pull
  07:10 — Garmin daily pull
  07:30 — Daily briefing
  09:00 Sunday — Weekly deep-dive
"""

import logging
import threading
import time
from datetime import datetime
from typing import Callable, Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")


class CronJob:
    """A single scheduled job."""

    def __init__(self, name: str, hour: int, minute: int, func: Callable,
                 day_of_week: Optional[int] = None):
        """
        Args:
            name: Human-readable job name.
            hour: Hour to run (0-23).
            minute: Minute to run (0-59).
            func: Callable to execute.
            day_of_week: If set, only run on this day (0=Monday, 6=Sunday).
        """
        self.name = name
        self.hour = hour
        self.minute = minute
        self.func = func
        self.day_of_week = day_of_week
        self.last_run: Optional[str] = None

    def should_run(self, now: datetime) -> bool:
        """Check if this job should run at the given time."""
        if now.hour != self.hour or now.minute != self.minute:
            return False
        if self.day_of_week is not None and now.weekday() != self.day_of_week:
            return False
        # Prevent double-runs within the same minute
        run_key = now.strftime("%Y-%m-%d %H:%M")
        if self.last_run == run_key:
            return False
        self.last_run = run_key
        return True

    def execute(self) -> None:
        """Run the job."""
        logger.info("Running job: %s", self.name)
        try:
            self.func()
            logger.info("Job completed: %s", self.name)
        except Exception as e:
            logger.error("Job failed: %s — %s", self.name, e)


class Scheduler:
    """Simple cron-like scheduler that checks jobs every 30 seconds."""

    def __init__(self):
        self.jobs: list[CronJob] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def add_job(self, name: str, hour: int, minute: int, func: Callable,
                day_of_week: Optional[int] = None) -> None:
        """Register a scheduled job."""
        self.jobs.append(CronJob(name, hour, minute, func, day_of_week))
        logger.info("Scheduled: %s at %02d:%02d%s",
                    name, hour, minute,
                    f" (day={day_of_week})" if day_of_week is not None else "")

    def _loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            now = datetime.now(ET)
            for job in self.jobs:
                if job.should_run(now):
                    # Run each job in its own thread to avoid blocking
                    t = threading.Thread(target=job.execute, daemon=True)
                    t.start()
            time.sleep(30)

    def start(self, background: bool = True) -> None:
        """Start the scheduler."""
        self._running = True
        if background:
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
            logger.info("Scheduler started in background with %d jobs", len(self.jobs))
        else:
            logger.info("Scheduler starting in foreground with %d jobs", len(self.jobs))
            self._loop()

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Scheduler stopped")


def create_default_scheduler(db_path: Optional[str] = None) -> Scheduler:
    """Create and configure the default health agent scheduler."""
    from healthcheck import run_healthcheck
    from clients.oura import pull_daily as oura_pull
    from clients.whoop import pull_daily as whoop_pull
    from clients.garmin import pull_daily as garmin_pull
    from briefing.generator import generate_briefing
    from telegram_bot import send_message

    s = Scheduler()

    # 06:00 — Healthcheck
    s.add_job("Healthcheck", 6, 0, lambda: run_healthcheck(db_path))

    # 07:00 — Oura pull
    s.add_job("Oura Pull", 7, 0, lambda: oura_pull(db_path=db_path))

    # 07:05 — Whoop pull
    s.add_job("Whoop Pull", 7, 5, lambda: whoop_pull(db_path=db_path))

    # 07:10 — Garmin pull
    s.add_job("Garmin Pull", 7, 10, lambda: garmin_pull(db_path=db_path))

    # 07:30 — Daily briefing
    def daily():
        result = generate_briefing(weekly=False, db_path=db_path)
        send_message(result["full_message"])

    s.add_job("Daily Briefing", 7, 30, daily)

    # 09:00 Sunday — Weekly deep-dive
    def weekly():
        result = generate_briefing(weekly=True, db_path=db_path)
        send_message(result["full_message"])

    s.add_job("Weekly Briefing", 9, 0, weekly, day_of_week=6)  # 6 = Sunday

    return s
