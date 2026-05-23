"""SMTP-based alert channel for cronwatch."""

import logging
import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import List

from cronwatch.alerts import AlertChannel, AlertEvent

logger = logging.getLogger(__name__)


@dataclass
class EmailChannel(AlertChannel):
    """Sends alert emails via SMTP."""

    smtp_host: str
    smtp_port: int
    sender: str
    recipients: List[str]
    username: str = ""
    password: str = ""
    use_tls: bool = True

    def send(self, event: AlertEvent) -> None:
        msg = EmailMessage()
        msg["Subject"] = event.subject()
        msg["From"] = self.sender
        msg["To"] = ", ".join(self.recipients)
        msg.set_content(_format_body(event))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as smtp:
                if self.use_tls:
                    smtp.starttls()
                if self.username:
                    smtp.login(self.username, self.password)
                smtp.send_message(msg)
            logger.info(
                "Email alert sent for job '%s' to %s",
                event.job_name,
                self.recipients,
            )
        except (smtplib.SMTPException, OSError) as exc:
            logger.error("Failed to send email alert for job '%s': %s", event.job_name, exc)


def _format_body(event: AlertEvent) -> str:
    lines = [
        f"Job:      {event.job_name}",
        f"Severity: {event.severity}",
        f"Kind:     {event.kind}",
        f"Message:  {event.message}",
    ]
    if event.timestamp:
        lines.append(f"Time:     {event.timestamp.isoformat()}")
    return "\n".join(lines)
