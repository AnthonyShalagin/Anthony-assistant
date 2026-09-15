"""Cron-based scheduler for daily health data pulls.

Schedule (Eastern Time):
  09:00 — Healthcheck (silent)
  09:30 — Oura daily pull (incl. workouts)
  09:35 — Whoop daily pull
  09:40 — Supabase sync for the dashboard
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

    s = Scheduler()

    # 09:00 — Healthcheck (silent — logs only, no Telegram)
    s.add_job("Healthcheck", 9, 0, lambda: run_healthcheck(db_path, notify=False))

    # 09:30 — Oura pull
    s.add_job("Oura Pull", 9, 30, lambda: oura_pull(db_path=db_path))

    # 09:35 — Whoop pull
    s.add_job("Whoop Pull", 9, 35, lambda: whoop_pull(db_path=db_path))

    # 09:40 — push fresh metrics + workouts to Supabase for the dashboard
    from supabase_sync import sync as supabase_sync
    s.add_job("Supabase Sync", 9, 40, lambda: supabase_sync(days=7, db_path=db_path))

    # No scheduled Telegram messages. The daily briefing went unread, so health
    # is now one section of the Sunday Life OS review on Anthony's Mac, which
    # reads this DB through export_week.py. Strong workouts arrive through
    # Apple Health -> Oura, so the monthly "export your CSV" reminder is gone.
    # generate_briefing is still available on demand via Jarvis.

    return s
