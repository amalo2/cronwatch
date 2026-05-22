"""Tests for WebhookChannel and its builder."""

from __future__ import annotations

import datetime
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import List

import pytest

from cronwatch.alerts import AlertEvent
from cronwatch.webhook import WebhookChannel, _event_to_dict
from cronwatch.webhook_builder import build_webhook_channel

_TS = datetime.datetime(2024, 6, 1, 12, 0, 0)


@pytest.fixture()
def event() -> AlertEvent:
    return AlertEvent(
        job_name="backup",
        severity="warning",
        message="Job overdue by 5 minutes",
        timestamp=_TS,
    )


# ---------------------------------------------------------------------------
# _event_to_dict
# ---------------------------------------------------------------------------

def test_event_to_dict_keys(event: AlertEvent) -> None:
    d = _event_to_dict(event)
    assert set(d) == {"subject", "job_name", "severity", "message", "timestamp"}


def test_event_to_dict_values(event: AlertEvent) -> None:
    d = _event_to_dict(event)
    assert d["job_name"] == "backup"
    assert d["severity"] == "warning"
    assert d["timestamp"] == _TS.isoformat()


def test_event_to_dict_none_timestamp() -> None:
    ev = AlertEvent(job_name="x", severity="info", message="m", timestamp=None)
    assert _event_to_dict(ev)["timestamp"] is None


# ---------------------------------------------------------------------------
# build_webhook_channel
# ---------------------------------------------------------------------------

def test_build_requires_url() -> None:
    with pytest.raises(ValueError, match="url"):
        build_webhook_channel({})


def test_build_defaults() -> None:
    ch = build_webhook_channel({"url": "http://example.com/hook"})
    assert ch.url == "http://example.com/hook"
    assert ch.timeout == 10
    assert ch.secret is None
    assert ch.headers == {}


def test_build_full_config() -> None:
    ch = build_webhook_channel(
        {"url": "https://h.io/w", "timeout": 5, "secret": "abc", "headers": {"X-Foo": "bar"}}
    )
    assert ch.timeout == 5
    assert ch.secret == "abc"
    assert ch.headers == {"X-Foo": "bar"}


# ---------------------------------------------------------------------------
# WebhookChannel.send — integration with a real local HTTP server
# ---------------------------------------------------------------------------

class _CaptureHandler(BaseHTTPRequestHandler):
    captured: List[dict] = []

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        _CaptureHandler.captured.append(
            {"path": self.path, "body": json.loads(body), "headers": dict(self.headers)}
        )
        self.send_response(200)
        self.end_headers()

    def log_message(self, *_: object) -> None:  # suppress output
        pass


@pytest.fixture()
def local_server():
    _CaptureHandler.captured.clear()
    srv = HTTPServer(("127.0.0.1", 0), _CaptureHandler)
    port = srv.server_address[1]
    t = Thread(target=srv.handle_request, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{port}/hook"
    srv.server_close()


def test_send_posts_json(local_server: str, event: AlertEvent) -> None:
    ch = WebhookChannel(url=local_server)
    ch.send(event)
    assert len(_CaptureHandler.captured) == 1
    body = _CaptureHandler.captured[0]["body"]
    assert body["job_name"] == "backup"


def test_send_includes_secret(local_server: str, event: AlertEvent) -> None:
    ch = WebhookChannel(url=local_server, secret="mysecret")
    ch.send(event)
    hdrs = _CaptureHandler.captured[0]["headers"]
    assert hdrs.get("X-Cronwatch-Secret") == "mysecret"
