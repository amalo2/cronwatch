"""Tests for cronwatch.detector — drift and silent-failure detection."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from cronwatch.alerts import AlertDispatcher, AlertEvent
from cronwatch.detector import DriftDetector
from cronwatch.job import JobConfig, JobState


def _config(**kwargs) -> JobConfig:
    defaults = dict(
        name="test_job",
        schedule="* * * * *",
        command="echo hi",
        drift_threshold_percent=20.0,
        silence_threshold_seconds=120,
        expected_duration_seconds=None,
    )
    defaults.update(kwargs)
    return JobConfig(**defaults)


def _state(**kwargs) -> JobState:
    return JobState(**kwargs)


@pytest.fixture()
def dispatcher() -> AlertDispatcher:
    d = AlertDispatcher(channels=[])
    d.dispatch = MagicMock()
    return d


def test_no_alert_when_no_history(dispatcher: AlertDispatcher) -> None:
    state = _state(last_run_at=None, recent_durations=[])
    detector = DriftDetector(_config(), state, dispatcher)
    detector.check(now=datetime(2024, 1, 1, 12, 0, 0))
    dispatcher.dispatch.assert_not_called()


def test_silent_failure_alert_when_overdue(dispatcher: AlertDispatcher) -> None:
    last_run = datetime(2024, 1, 1, 11, 0, 0)
    now = last_run + timedelta(seconds=300)  # 300s > 120s threshold
    state = _state(last_run_at=last_run, recent_durations=[])
    detector = DriftDetector(_config(), state, dispatcher)
    detector.check(now=now)

    dispatcher.dispatch.assert_called_once()
    event: AlertEvent = dispatcher.dispatch.call_args[0][0]
    assert event.kind == "silent_failure"
    assert event.severity == "critical"


def test_no_silent_failure_within_threshold(dispatcher: AlertDispatcher) -> None:
    last_run = datetime(2024, 1, 1, 12, 0, 0)
    now = last_run + timedelta(seconds=60)  # 60s < 120s threshold
    state = _state(last_run_at=last_run, recent_durations=[])
    detector = DriftDetector(_config(), state, dispatcher)
    detector.check(now=now)
    dispatcher.dispatch.assert_not_called()


def test_drift_alert_when_duration_exceeds_threshold(dispatcher: AlertDispatcher) -> None:
    # baseline=10s, latest=15s → 50% drift > 20% threshold
    state = _state(last_run_at=datetime(2024, 1, 1, 12, 0, 0), recent_durations=[10.0, 15.0])
    detector = DriftDetector(_config(expected_duration_seconds=10.0), state, dispatcher)
    detector.check(now=datetime(2024, 1, 1, 12, 0, 30))

    calls = [c[0][0] for c in dispatcher.dispatch.call_args_list]
    drift_events = [e for e in calls if e.kind == "drift"]
    assert len(drift_events) == 1
    assert drift_events[0].severity == "critical"  # 50% > 40% (2x threshold)


def test_no_drift_alert_within_threshold(dispatcher: AlertDispatcher) -> None:
    # baseline=10s, latest=10.5s → 5% drift < 20%
    state = _state(last_run_at=datetime(2024, 1, 1, 12, 0, 0), recent_durations=[10.0, 10.5])
    detector = DriftDetector(_config(expected_duration_seconds=10.0), state, dispatcher)
    detector.check(now=datetime(2024, 1, 1, 12, 0, 30))

    calls = [c[0][0] for c in dispatcher.dispatch.call_args_list]
    drift_events = [e for e in calls if e.kind == "drift"]
    assert len(drift_events) == 0


def test_drift_uses_first_duration_as_baseline_when_no_expected(dispatcher: AlertDispatcher) -> None:
    state = _state(last_run_at=datetime(2024, 1, 1, 12, 0, 0), recent_durations=[5.0, 9.0])
    detector = DriftDetector(_config(expected_duration_seconds=None), state, dispatcher)
    detector.check(now=datetime(2024, 1, 1, 12, 0, 30))

    calls = [c[0][0] for c in dispatcher.dispatch.call_args_list]
    drift_events = [e for e in calls if e.kind == "drift"]
    assert len(drift_events) == 1  # 80% drift
