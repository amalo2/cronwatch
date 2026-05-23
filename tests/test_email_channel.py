"""Tests for EmailChannel and build_email_channel."""

import smtplib
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.alerts import AlertEvent
from cronwatch.email_builder import build_email_channel
from cronwatch.email_channel import EmailChannel, _format_body


@pytest.fixture()
def event() -> AlertEvent:
    return AlertEvent(
        job_name="backup",
        kind="silent_failure",
        severity="critical",
        message="Job has not run in 2h",
        timestamp=datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture()
def channel() -> EmailChannel:
    return EmailChannel(
        smtp_host="localhost",
        smtp_port=1025,
        sender="alerts@example.com",
        recipients=["ops@example.com"],
        use_tls=False,
    )


# ── format helpers ────────────────────────────────────────────────────────────

def test_format_body_contains_job_name(event):
    body = _format_body(event)
    assert "backup" in body


def test_format_body_contains_message(event):
    body = _format_body(event)
    assert "Job has not run in 2h" in body


def test_format_body_contains_timestamp(event):
    body = _format_body(event)
    assert "2024-06-01" in body


def test_format_body_no_timestamp(event):
    event.timestamp = None
    body = _format_body(event)
    assert "Time:" not in body


# ── send (happy path) ─────────────────────────────────────────────────────────

def test_send_calls_smtp(channel, event):
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = lambda s: mock_smtp
    mock_smtp.__exit__ = MagicMock(return_value=False)

    with patch("smtplib.SMTP", return_value=mock_smtp):
        channel.send(event)

    mock_smtp.send_message.assert_called_once()


def test_send_skips_tls_when_disabled(channel, event):
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = lambda s: mock_smtp
    mock_smtp.__exit__ = MagicMock(return_value=False)

    with patch("smtplib.SMTP", return_value=mock_smtp):
        channel.send(event)

    mock_smtp.starttls.assert_not_called()


def test_send_uses_tls_when_enabled(channel, event):
    channel.use_tls = True
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = lambda s: mock_smtp
    mock_smtp.__exit__ = MagicMock(return_value=False)

    with patch("smtplib.SMTP", return_value=mock_smtp):
        channel.send(event)

    mock_smtp.starttls.assert_called_once()


# ── send (error handling) ─────────────────────────────────────────────────────

def test_smtp_error_is_logged_not_raised(channel, event, caplog):
    with patch("smtplib.SMTP", side_effect=smtplib.SMTPException("boom")):
        channel.send(event)  # must not raise

    assert "backup" in caplog.text


def test_os_error_is_logged_not_raised(channel, event, caplog):
    with patch("smtplib.SMTP", side_effect=OSError("connection refused")):
        channel.send(event)

    assert "backup" in caplog.text


# ── builder ───────────────────────────────────────────────────────────────────

def test_build_requires_smtp_host():
    with pytest.raises(ValueError, match="smtp_host"):
        build_email_channel({"sender": "a@b.com", "recipients": ["x@y.com"]})


def test_build_requires_sender():
    with pytest.raises(ValueError, match="sender"):
        build_email_channel({"smtp_host": "localhost", "recipients": ["x@y.com"]})


def test_build_requires_recipients():
    with pytest.raises(ValueError, match="recipient"):
        build_email_channel({"smtp_host": "localhost", "sender": "a@b.com"})


def test_build_defaults(channel):
    ch = build_email_channel(
        {
            "smtp_host": "localhost",
            "sender": "a@b.com",
            "recipients": ["x@y.com"],
        }
    )
    assert ch.smtp_port == 587
    assert ch.use_tls is True
    assert ch.username == ""


def test_build_custom_port():
    ch = build_email_channel(
        {
            "smtp_host": "localhost",
            "smtp_port": 2525,
            "sender": "a@b.com",
            "recipients": ["x@y.com"],
        }
    )
    assert ch.smtp_port == 2525
