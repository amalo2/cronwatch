"""Rate-limited notification wrapper that suppresses duplicate alerts."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from cronwatch.alerts import AlertDispatcher, AlertEvent

logger = logging.getLogger(__name__)

# Key: (job_name, alert_kind)  Value: last time the alert was dispatched
_SentKey = Tuple[str, str]


@dataclass
class Notifier:
    """Wraps an AlertDispatcher and suppresses repeated alerts within a cooldown window."""

    dispatcher: AlertDispatcher
    cooldown: timedelta = field(default_factory=lambda: timedelta(minutes=30))
    _last_sent: Dict[_SentKey, datetime] = field(default_factory=dict, init=False, repr=False)

    def notify(self, event: AlertEvent, *, now: Optional[datetime] = None) -> bool:
        """Dispatch *event* unless an identical alert was sent within the cooldown period.

        Returns True if the alert was dispatched, False if it was suppressed.
        """
        now = now or datetime.utcnow()
        key: _SentKey = (event.job_name, event.kind)
        last = self._last_sent.get(key)

        if last is not None and (now - last) < self.cooldown:
            logger.debug(
                "Suppressing duplicate alert '%s' for job '%s' (last sent %s ago)",
                event.kind,
                event.job_name,
                now - last,
            )
            return False

        self.dispatcher.dispatch(event)
        self._last_sent[key] = now
        logger.debug("Alert '%s' dispatched for job '%s'", event.kind, event.job_name)
        return True

    def reset(self, job_name: str, kind: str) -> None:
        """Clear the cooldown state for a specific (job_name, kind) pair."""
        self._last_sent.pop((job_name, kind), None)

    def reset_all(self) -> None:
        """Clear all cooldown state (useful for testing or config reloads)."""
        self._last_sent.clear()
