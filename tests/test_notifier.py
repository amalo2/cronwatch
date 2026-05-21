"""Tests for cronwatch.notifier.Notifier."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, call

import pytest

from cronwatch.alerts import AlertDispatcher, AlertEvent
from cronwatch.notifier import Notifier


def _event(job_name: str = "backup", kind: str = "silent_failure", severity: str = "critical") -> AlertEvent:
    return AlertEvent(
        job_name=job_name,
        kind=kind,
        severity=severity,
        message="Test alert",
        timestamp=datetime(2024, 1, 15, 10, 0, 0),
    )


@pytest.fixture()
def dispatcher() -> MagicMock:
    d = MagicMock(spec=AlertDispatcher)
    return d


@pytest.fixture()
def notifier(dispatcher: MagicMock) -> Notifier:
    return Notifier(dispatcher=dispatcher, cooldown=timedelta(minutes=30))


def test_first_alert_is_dispatched(notifier: Notifier, dispatcher: MagicMock) -> None:
    event = _event()
    result = notifier.notify(event, now=datetime(2024, 1, 15, 10, 0, 0))
    assert result is True
    dispatcher.dispatch.assert_called_once_with(event)


def test_duplicate_within_cooldown_is_suppressed(notifier: Notifier, dispatcher: MagicMock) -> None:
    t0 = datetime(2024, 1, 15, 10, 0, 0)
    t1 = t0 + timedelta(minutes=15)  # within 30-min cooldown
    event = _event()
    notifier.notify(event, now=t0)
    result = notifier.notify(event, now=t1)
    assert result is False
    dispatcher.dispatch.assert_called_once()  # only the first call


def test_alert_after_cooldown_is_dispatched(notifier: Notifier, dispatcher: MagicMock) -> None:
    t0 = datetime(2024, 1, 15, 10, 0, 0)
    t1 = t0 + timedelta(minutes=31)  # past cooldown
    event = _event()
    notifier.notify(event, now=t0)
    result = notifier.notify(event, now=t1)
    assert result is True
    assert dispatcher.dispatch.call_count == 2


def test_different_kinds_are_independent(notifier: Notifier, dispatcher: MagicMock) -> None:
    t0 = datetime(2024, 1, 15, 10, 0, 0)
    e1 = _event(kind="silent_failure")
    e2 = _event(kind="drift")
    notifier.notify(e1, now=t0)
    result = notifier.notify(e2, now=t0)
    assert result is True
    assert dispatcher.dispatch.call_count == 2


def test_different_jobs_are_independent(notifier: Notifier, dispatcher: MagicMock) -> None:
    t0 = datetime(2024, 1, 15, 10, 0, 0)
    e1 = _event(job_name="backup")
    e2 = _event(job_name="cleanup")
    notifier.notify(e1, now=t0)
    result = notifier.notify(e2, now=t0)
    assert result is True
    assert dispatcher.dispatch.call_count == 2


def test_reset_clears_cooldown_for_key(notifier: Notifier, dispatcher: MagicMock) -> None:
    t0 = datetime(2024, 1, 15, 10, 0, 0)
    event = _event()
    notifier.notify(event, now=t0)
    notifier.reset(event.job_name, event.kind)
    result = notifier.notify(event, now=t0)  # same time, but cooldown cleared
    assert result is True
    assert dispatcher.dispatch.call_count == 2


def test_reset_all_clears_all_state(notifier: Notifier, dispatcher: MagicMock) -> None:
    t0 = datetime(2024, 1, 15, 10, 0, 0)
    notifier.notify(_event(job_name="a"), now=t0)
    notifier.notify(_event(job_name="b"), now=t0)
    notifier.reset_all()
    notifier.notify(_event(job_name="a"), now=t0)
    notifier.notify(_event(job_name="b"), now=t0)
    assert dispatcher.dispatch.call_count == 4
