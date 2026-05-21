"""Alert channels for cronwatch drift and failure notifications."""

from __future__ import annotations

import logging
import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class AlertEvent:
    """Represents a single alert to be dispatched."""

    job_name: str
    kind: str  # 'drift' | 'silent_failure' | 'error'
    message: str
    severity: str = "warning"  # 'info' | 'warning' | 'critical'
    extra: dict = field(default_factory=dict)

    def subject(self) -> str:
        return f"[cronwatch][{self.severity.upper()}] {self.kind} — {self.job_name}"


class AlertChannel(ABC):
    """Base class for alert channels."""

    @abstractmethod
    def send(self, event: AlertEvent) -> None:
        """Send an alert event through this channel."""


class LogChannel(AlertChannel):
    """Writes alerts to the Python logging system."""

    _level_map = {
        "info": logging.INFO,
        "warning": logging.WARNING,
        "critical": logging.CRITICAL,
    }

    def send(self, event: AlertEvent) -> None:
        level = self._level_map.get(event.severity, logging.WARNING)
        logger.log(level, "%s | %s | %s", event.job_name, event.kind, event.message)


@dataclass
class SmtpChannel(AlertChannel):
    """Sends alerts via SMTP email."""

    host: str
    port: int
    sender: str
    recipients: list[str]
    username: Optional[str] = None
    password: Optional[str] = None
    use_tls: bool = True

    def send(self, event: AlertEvent) -> None:
        msg = EmailMessage()
        msg["Subject"] = event.subject()
        msg["From"] = self.sender
        msg["To"] = ", ".join(self.recipients)
        msg.set_content(event.message)

        try:
            cls = smtplib.SMTP_SSL if self.use_tls else smtplib.SMTP
            with cls(self.host, self.port) as smtp:
                if self.username and self.password:
                    smtp.login(self.username, self.password)
                smtp.send_message(msg)
            logger.debug("Alert email sent for job '%s'", event.job_name)
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to send alert email: %s", exc)


class AlertDispatcher:
    """Dispatches AlertEvents to one or more channels."""

    def __init__(self, channels: Optional[list[AlertChannel]] = None) -> None:
        self.channels: list[AlertChannel] = channels or [LogChannel()]

    def add_channel(self, channel: AlertChannel) -> None:
        self.channels.append(channel)

    def dispatch(self, event: AlertEvent) -> None:
        for channel in self.channels:
            try:
                channel.send(event)
            except Exception as exc:  # pragma: no cover
                logger.error("Alert channel %s failed: %s", type(channel).__name__, exc)
