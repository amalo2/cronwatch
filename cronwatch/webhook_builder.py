"""Factory helpers for constructing WebhookChannel from config dicts."""

from __future__ import annotations

from typing import Any, Dict

from cronwatch.webhook import WebhookChannel


def build_webhook_channel(cfg: Dict[str, Any]) -> WebhookChannel:
    """Build a :class:`WebhookChannel` from a raw config mapping.

    Expected keys:
      - ``url`` (required): destination endpoint.
      - ``timeout`` (optional, int): request timeout in seconds.
      - ``secret`` (optional, str): shared secret sent as a header.
      - ``headers`` (optional, dict): extra HTTP headers.

    Raises
    ------
    ValueError
        If ``url`` is missing or empty.
    """
    url = cfg.get("url", "").strip()
    if not url:
        raise ValueError("WebhookChannel requires a non-empty 'url'")

    timeout = int(cfg.get("timeout", 10))
    secret = cfg.get("secret") or None
    headers: Dict[str, str] = dict(cfg.get("headers") or {})

    return WebhookChannel(url=url, timeout=timeout, secret=secret, headers=headers)
