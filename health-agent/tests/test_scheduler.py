"""Tests for the scheduler module."""

from datetime import datetime
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

from scheduler import CronJob, Scheduler

ET = ZoneInfo("America/New_York")


def test_cronjob_should_run_correct_time():
    """Job should run at the scheduled time."""
    job = CronJob("test", 7, 30, lambda: None)
    now = datetime(2024, 3, 15, 7, 30, tzinfo=ET)
    assert job.should_run(now) is True


def test_cronjob_should_not_run_wrong_time():
    """Job should not run at the wrong time."""
    job = CronJob("test", 7, 30, lambda: None)
    now = datetime(2024, 3, 15, 8, 0, tzinfo=ET)
    assert job.should_run(now) is False


def test_cronjob_day_of_week_match():
    """Job with day_of_week runs on the correct day."""
    # 2024-03-17 is a Sunday (weekday=6)
    job = CronJob("weekly", 9, 0, lambda: None, day_of_week=6)
    sunday = datetime(2024, 3, 17, 9, 0, tzinfo=ET)
    assert job.should_run(sunday) is True


def test_cronjob_day_of_week_mismatch():
    """Job with day_of_week skips other days."""
    job = CronJob("weekly", 9, 0, lambda: None, day_of_week=6)
    monday = datetime(2024, 3, 18, 9, 0, tzinfo=ET)
    assert job.should_run(monday) is False


def test_cronjob_no_double_run():
    """Job does not run twice in the same minute."""
    func = MagicMock()
    job = CronJob("test", 7, 30, func)
    now = datetime(2024, 3, 15, 7, 30, tzinfo=ET)

    assert job.should_run(now) is True
    job.execute()
    assert job.should_run(now) is False


def test_cronjob_execute_calls_func():
    """execute() calls the registered function."""
    func = MagicMock()
    job = CronJob("test", 7, 30, func)
    job.execute()
    func.assert_called_once()


def test_scheduler_add_job():
    """Scheduler registers jobs."""
    s = Scheduler()
    s.add_job("test1", 7, 0, lambda: None)
    s.add_job("test2", 7, 30, lambda: None)
    assert len(s.jobs) == 2
