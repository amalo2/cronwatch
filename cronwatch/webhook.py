"""Webhook alert channel — POSTs AlertEvent payloads to a configured URL."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from cronwatch.alerts import AlertChannel, AlertEvent

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 10  # seconds


@dataclass
class WebhookChannel(AlertChannel):
    """Send alert events as JSON POST requests to a webhook URL."""

    url: str
    timeout: int = _DEFAULT_TIMEOUT
    headers: Dict[str, str] = field(default_factory=dict)
    # Optional secret added as X-Cronwatch-Secret header
    secret: Optional[str] = None

    def send(self, event: AlertEvent) -> None:  # noqa: D102
        payload = _event_to_dict(event)
        body = json.dumps(payload).encode()

        req_headers = {"Content-Type": "application/json", **self.headers}
        if self.secret:
            req_headers["X-Cronwatch-Secret"] = self.secret

        req = urllib.request.Request(
            self.url, data=body, headers=req_headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status = resp.status
                logger.debug("Webhook delivered: status=%s url=%s", status, self.url)
        except urllib.error.HTTPError as exc:
            logger.error(
                "Webhook HTTP error: status=%s url=%s", exc.code, self.url
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Webhook delivery failed: %s url=%s", exc, self.url)


def _event_to_dict(event: AlertEvent) -> Dict[str, Any]:
    return {
        "subject": event.subject,
        "job_name": event.job_name,
        "severity": event.severity,
        "message": event.message,
        "timestamp": event.timestamp.isoformat() if event.timestamp else None,
    }
