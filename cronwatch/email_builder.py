"""Build an EmailChannel from a config dictionary."""

from typing import Any, Dict

from cronwatch.email_channel import EmailChannel


def build_email_channel(cfg: Dict[str, Any]) -> EmailChannel:
    """Construct an EmailChannel from a raw config dict.

    Expected keys:
        smtp_host (str)           – required
        smtp_port (int)           – default 587
        sender    (str)           – required
        recipients (list[str])    – required, at least one address
        username  (str)           – optional
        password  (str)           – optional
        use_tls   (bool)          – default True
    """
    host = cfg.get("smtp_host")
    if not host:
        raise ValueError("email channel requires 'smtp_host'")

    sender = cfg.get("sender")
    if not sender:
        raise ValueError("email channel requires 'sender'")

    recipients = cfg.get("recipients", [])
    if not recipients:
        raise ValueError("email channel requires at least one recipient")

    return EmailChannel(
        smtp_host=host,
        smtp_port=int(cfg.get("smtp_port", 587)),
        sender=sender,
        recipients=list(recipients),
        username=cfg.get("username", ""),
        password=cfg.get("password", ""),
        use_tls=bool(cfg.get("use_tls", True)),
    )
