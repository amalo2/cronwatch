"""Load cronwatch configuration from a YAML file."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

from cronwatch.alerts import AlertChannel, Dispatcher, LogChannel
from cronwatch.job import JobConfig
from cronwatch.webhook_builder import build_webhook_channel

logger = logging.getLogger(__name__)


def load_config(path: str | Path) -> tuple[List[JobConfig], Dispatcher]:
    """Parse *path* and return (jobs, dispatcher)."""
    if yaml is None:  # pragma: no cover
        raise RuntimeError("PyYAML is required to load configuration files")

    raw: Dict[str, Any] = yaml.safe_load(Path(path).read_text()) or {}

    jobs = [_build_job(j) for j in raw.get("jobs", [])]
    dispatcher = _build_dispatcher(raw.get("alerts", {}))
    return jobs, dispatcher


def _build_job(cfg: Dict[str, Any]) -> JobConfig:
    return JobConfig(
        name=cfg["name"],
        schedule=cfg["schedule"],
        max_drift_seconds=int(cfg.get("max_drift_seconds", 300)),
        silent_failure_multiplier=float(cfg.get("silent_failure_multiplier", 2.0)),
    )


def _build_dispatcher(cfg: Dict[str, Any]) -> Dispatcher:
    channels: List[AlertChannel] = []

    # Always include the log channel so there is at least one output
    channels.append(LogChannel())

    for ch_cfg in cfg.get("channels", []):
        kind = ch_cfg.get("type", "").lower()
        if kind == "webhook":
            try:
                channels.append(build_webhook_channel(ch_cfg))
            except ValueError as exc:
                logger.warning("Skipping invalid webhook channel config: %s", exc)
        elif kind == "log":
            pass  # already added above
        else:
            logger.warning("Unknown alert channel type: %r — ignoring", kind)

    return Dispatcher(channels=channels)
