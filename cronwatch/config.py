"""Load and validate cronwatch configuration from a YAML file."""

import logging
from pathlib import Path
from typing import Any, Dict

import yaml

from cronwatch.alerts import AlertChannel, Dispatcher
from cronwatch.email_builder import build_email_channel
from cronwatch.job import JobConfig
from cronwatch.webhook_builder import build_webhook_channel

logger = logging.getLogger(__name__)


def load_config(path: str | Path) -> Dict[str, Any]:
    """Parse YAML config and return a dict with 'jobs' and 'dispatcher'."""
    with open(path) as fh:
        raw = yaml.safe_load(fh) or {}

    jobs = {name: _build_job(name, spec) for name, spec in raw.get("jobs", {}).items()}
    dispatcher = _build_dispatcher(raw.get("alerts", {}))

    return {"jobs": jobs, "dispatcher": dispatcher}


def _build_job(name: str, spec: Dict[str, Any]) -> JobConfig:
    return JobConfig(
        name=name,
        schedule=spec["schedule"],
        expected_duration_s=spec.get("expected_duration_s"),
        drift_threshold_s=spec.get("drift_threshold_s", 300),
        silence_threshold_s=spec.get("silence_threshold_s", 3600),
    )


def _build_dispatcher(alert_cfg: Dict[str, Any]) -> "Dispatcher":
    from cronwatch.alerts import Dispatcher  # local to avoid circular import

    channels: list[AlertChannel] = []

    for ch_cfg in alert_cfg.get("channels", []):
        kind = ch_cfg.get("type", "")
        try:
            if kind == "webhook":
                channels.append(build_webhook_channel(ch_cfg))
            elif kind == "email":
                channels.append(build_email_channel(ch_cfg))
            else:
                logger.warning("Unknown alert channel type '%s'; skipping.", kind)
        except (ValueError, KeyError) as exc:
            logger.error("Failed to build channel of type '%s': %s", kind, exc)

    return Dispatcher(channels=channels)
