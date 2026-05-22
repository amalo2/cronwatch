"""Tests for the Prometheus-compatible metrics HTTP server."""

import threading
import time
import urllib.request
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.metrics_server import MetricsServer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _free_port() -> int:
    """Return an ephemeral port that is (probably) free."""
    import socket
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _get(url: str, timeout: float = 3.0) -> tuple[int, str]:
    """Perform a GET request and return (status_code, body)."""
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.status, resp.read().decode()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_collector():
    """A callable that returns a fixed metrics text payload."""
    return MagicMock(return_value="# HELP cronwatch_up Up\ncronwatch_up 1\n")


@pytest.fixture()
def server(mock_collector):
    """Start a MetricsServer on a free port and stop it after the test."""
    port = _free_port()
    srv = MetricsServer(port=port, collector=mock_collector)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    # Give the server a moment to bind
    time.sleep(0.05)
    yield srv, port
    srv.shutdown()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMetricsServer:
    def test_get_metrics_returns_200(self, server):
        """GET /metrics should respond with HTTP 200."""
        _, port = server
        status, _ = _get(f"http://127.0.0.1:{port}/metrics")
        assert status == 200

    def test_get_metrics_returns_text_plain(self, server):
        """Response Content-Type should indicate plain text."""
        _, port = server
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/metrics", timeout=3
        ) as resp:
            ct = resp.headers.get("Content-Type", "")
        assert "text/plain" in ct

    def test_get_metrics_body_contains_collector_output(self, server, mock_collector):
        """Response body should equal what the collector returns."""
        _, port = server
        _, body = _get(f"http://127.0.0.1:{port}/metrics")
        assert "cronwatch_up 1" in body

    def test_collector_is_called_on_each_request(self, server, mock_collector):
        """Collector callable should be invoked once per HTTP request."""
        _, port = server
        _get(f"http://127.0.0.1:{port}/metrics")
        _get(f"http://127.0.0.1:{port}/metrics")
        assert mock_collector.call_count == 2

    def test_unknown_path_returns_404(self, server):
        """Any path other than /metrics should return HTTP 404."""
        _, port = server
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            _get(f"http://127.0.0.1:{port}/unknown")
        assert exc_info.value.code == 404

    def test_root_path_returns_404(self, server):
        """Root path / is not a valid endpoint."""
        _, port = server
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            _get(f"http://127.0.0.1:{port}/")
        assert exc_info.value.code == 404

    def test_server_binds_to_specified_port(self, mock_collector):
        """MetricsServer should bind to the port passed at construction."""
        port = _free_port()
        srv = MetricsServer(port=port, collector=mock_collector)
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        time.sleep(0.05)
        try:
            status, _ = _get(f"http://127.0.0.1:{port}/metrics")
            assert status == 200
        finally:
            srv.shutdown()
