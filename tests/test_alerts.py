"""Tests for cronwatch.alerts."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cronwatch.alerts import AlertDispatcher, AlertEvent, LogChannel, SmtpChannel


@pytest.fixture()
def event() -> AlertEvent:
    return AlertEvent(
        job_name="backup",
        kind="drift",
        message="Duration drifted 35%",
        severity="warning",
    )


def test_alert_event_subject(event: AlertEvent) -> None:
    assert event.subject() == "[cronwatch][WARNING] drift — backup"


def test_log_channel_sends_without_error(event: AlertEvent, caplog) -> None:
    import logging

    channel = LogChannel()
    with caplog.at_level(logging.WARNING, logger="cronwatch.alerts"):
        channel.send(event)
    assert "backup" in caplog.text
    assert "drift" in caplog.text


def test_log_channel_critical_severity(caplog) -> None:
    import logging

    ev = AlertEvent(
        job_name="myjob", kind="silent_failure", message="overdue", severity="critical"
    )
    channel = LogChannel()
    with caplog.at_level(logging.CRITICAL, logger="cronwatch.alerts"):
        channel.send(ev)
    assert "myjob" in caplog.text


def test_dispatcher_calls_all_channels(event: AlertEvent) -> None:
    ch1 = MagicMock()
    ch2 = MagicMock()
    dispatcher = AlertDispatcher(channels=[ch1, ch2])
    dispatcher.dispatch(event)
    ch1.send.assert_called_once_with(event)
    ch2.send.assert_called_once_with(event)


def test_dispatcher_add_channel(event: AlertEvent) -> None:
    dispatcher = AlertDispatcher(channels=[])
    ch = MagicMock()
    dispatcher.add_channel(ch)
    dispatcher.dispatch(event)
    ch.send.assert_called_once_with(event)


def test_dispatcher_default_log_channel(event: AlertEvent) -> None:
    dispatcher = AlertDispatcher()
    assert len(dispatcher.channels) == 1
    assert isinstance(dispatcher.channels[0], LogChannel)


def test_smtp_channel_sends_email(event: AlertEvent) -> None:
    channel = SmtpChannel(
        host="smtp.example.com",
        port=465,
        sender="cronwatch@example.com",
        recipients=["ops@example.com"],
        use_tls=True,
    )
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = lambda s: mock_smtp
    mock_smtp.__exit__ = MagicMock(return_value=False)

    with patch("smtplib.SMTP_SSL", return_value=mock_smtp):
        channel.send(event)

    mock_smtp.send_message.assert_called_once()
