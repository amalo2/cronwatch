"""Tests for CronSchedule parsing and JobState logic."""

import pytest
from datetime import datetime, timezone

from cronwatch.schedule import CronSchedule
from cronwatch.job import JobConfig, JobState


# ---------------------------------------------------------------------------
# CronSchedule tests
# ---------------------------------------------------------------------------

def _dt(minute=0, hour=0, day=1, month=1, weekday=0):
    """Build a UTC datetime with the given components (weekday ignored by datetime)."""
    # Use a fixed Monday (weekday=0) base date and adjust hour/minute only.
    return datetime(2024, 1, 1, hour, minute, 0, tzinfo=timezone.utc)


def test_wildcard_matches_any_time():
    s = CronSchedule("* * * * *")
    assert s.matches(_dt(minute=30, hour=14))


def test_specific_minute_and_hour():
    s = CronSchedule("30 14 * * *")
    assert s.matches(_dt(minute=30, hour=14))
    assert not s.matches(_dt(minute=31, hour=14))
    assert not s.matches(_dt(minute=30, hour=15))


def test_step_expression():
    s = CronSchedule("*/15 * * * *")
    for minute in (0, 15, 30, 45):
        assert s.matches(_dt(minute=minute))
    assert not s.matches(_dt(minute=7))


def test_range_expression():
    s = CronSchedule("0 9-17 * * *")
    assert s.matches(_dt(minute=0, hour=12))
    assert not s.matches(_dt(minute=0, hour=8))
    assert not s.matches(_dt(minute=0, hour=18))


def test_invalid_expression_raises():
    with pytest.raises(ValueError, match="expected 5 fields"):
        CronSchedule("* * * *")


# ---------------------------------------------------------------------------
# JobState tests
# ---------------------------------------------------------------------------

def _make_state(grace=120, timeout=None):
    cfg = JobConfig(name="test-job", schedule="* * * * *", grace_seconds=grace, timeout_seconds=timeout)
    return JobState(config=cfg)


def test_record_execution_resets_failure_count():
    state = _make_state()
    state.failure_count = 3
    now = datetime.now(tz=timezone.utc)
    state.record_execution(now, duration_seconds=5.0)
    assert state.failure_count == 0
    assert state.last_duration_seconds == 5.0


def test_is_overdue_when_past_grace():
    state = _make_state(grace=60)
    past = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    state.last_seen = past
    future = datetime(2024, 1, 1, 0, 2, 1, tzinfo=timezone.utc)  # 121 s later
    assert state.is_overdue(now=future)


def test_not_overdue_within_grace():
    state = _make_state(grace=120)
    past = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    state.last_seen = past
    soon = datetime(2024, 1, 1, 0, 1, 0, tzinfo=timezone.utc)  # 60 s later
    assert not state.is_overdue(now=soon)


def test_is_timed_out():
    state = _make_state(timeout=30)
    state.last_duration_seconds = 45.0
    assert state.is_timed_out()


def test_not_timed_out_without_timeout_config():
    state = _make_state(timeout=None)
    state.last_duration_seconds = 999.0
    assert not state.is_timed_out()
