"""Tests for WebhookChannel error / failure paths."""

from __future__ import annotations

import datetime
import logging
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.alerts import AlertEvent
from cronwatch.webhook import WebhookChannel

_TS = datetime.datetime(2024, 6, 1, 9, 0, 0)


@pytest.fixture()
def event() -> AlertEvent:
    return AlertEvent(
        job_name="nightly",
        severity="critical",
        message="silent failure detected",
        timestamp=_TS,
    )


def test_http_error_is_logged(event: AlertEvent, caplog: pytest.LogCaptureFixture) -> None:
    ch = WebhookChannel(url="http://example.invalid/hook")
    http_err = urllib.error.HTTPError(
        url="http://example.invalid/hook",
        code=500,
        msg="Internal Server Error",
        hdrs=MagicMock(),  # type: ignore[arg-type]
        fp=None,  # type: ignore[arg-type]
    )
    with patch("urllib.request.urlopen", side_effect=http_err):
        with caplog.at_level(logging.ERROR, logger="cronwatch.webhook"):
            ch.send(event)  # must not raise
    assert "500" in caplog.text


def test_connection_error_is_logged(event: AlertEvent, caplog: pytest.LogCaptureFixture) -> None:
    ch = WebhookChannel(url="http://example.invalid/hook")
    with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
        with caplog.at_level(logging.ERROR, logger="cronwatch.webhook"):
            ch.send(event)
    assert "connection refused" in caplog.text


def test_no_exception_propagated(event: AlertEvent) -> None:
    ch = WebhookChannel(url="http://example.invalid/hook")
    with patch("urllib.request.urlopen", side_effect=RuntimeError("boom")):
        ch.send(event)  # should swallow the error silently
