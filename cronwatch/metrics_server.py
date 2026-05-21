"""Tiny HTTP server that exposes cronwatch metrics on /metrics."""
from __future__ import annotations

import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable

logger = logging.getLogger(__name__)


def _make_handler(get_metrics: Callable[[], str]) -> type:
    """Create a request-handler class bound to *get_metrics*."""

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/metrics":
                body = get_metrics().encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; version=0.0.4")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, fmt: str, *args: object) -> None:  # noqa: N802
            logger.debug(fmt, *args)

    return _Handler


class MetricsServer:
    """Background HTTP server thread that serves metrics."""

    def __init__(self, get_metrics: Callable[[], str], host: str = "0.0.0.0", port: int = 9090) -> None:
        self._get_metrics = get_metrics
        self._host = host
        self._port = port
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        handler_cls = _make_handler(self._get_metrics)
        self._server = HTTPServer((self._host, self._port), handler_cls)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        logger.info("Metrics server listening on %s:%s", self._host, self._port)

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            logger.info("Metrics server stopped")
