"""Tests for cronwatch.watcher.Watcher."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.job import JobConfig, JobState
from cronwatch.watcher import Watcher


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

_MINIMAL_CONFIG = """
jobs:
  - name: backup
    schedule: "0 2 * * *"
    drift_threshold_minutes: 10
    silence_timeout_minutes: 1500

alerts:
  channels: []
"""


@pytest.fixture()
def watcher(tmp_path):
    cfg_file = tmp_path / "cronwatch.yaml"
    cfg_file.write_text(_MINIMAL_CONFIG)
    return Watcher(str(cfg_file), poll_interval=1)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_watcher_loads_jobs(watcher):
    assert "backup" in watcher.jobs
    assert "backup" in watcher._states
    assert "backup" in watcher._detectors


def test_record_execution_updates_state(watcher):
    before = watcher._states["backup"].last_run_at
    watcher.record_execution("backup", 4.2)
    after = watcher._states["backup"].last_run_at
    assert after is not None
    assert before != after


def test_record_execution_stores_duration(watcher):
    """record_execution should persist the reported duration on the job state."""
    watcher.record_execution("backup", 7.5)
    assert watcher._states["backup"].last_duration == 7.5


def test_record_execution_unknown_job_logs_warning(watcher, caplog):
    import logging

    with caplog.at_level(logging.WARNING, logger="cronwatch.watcher"):
        watcher.record_execution("nonexistent", 1.0)
    assert "unknown job" in caplog.text


def test_check_all_calls_detector_for_each_job(watcher):
    mock_detector = MagicMock()
    watcher._detectors["backup"] = mock_detector

    watcher.check_all()

    mock_detector.check.assert_called_once()
    call_args = mock_detector.check.call_args
    assert isinstance(call_args[0][0], JobState)
    assert isinstance(call_args[0][1], datetime)


def test_check_all_passes_utc_now(watcher):
    captured: list[datetime] = []

    def fake_check(state, now):
        captured.append(now)

    watcher._detectors["backup"].check = fake_check
    watcher.check_all()

    assert len(captured) == 1
    assert captured[0].tzinfo is not None  # timezone-aware


def test_watcher_unknown_job_does_not_raise(watcher):
    # Should log a warning, not raise
    watcher.record_execution("ghost_job", 0.5)
