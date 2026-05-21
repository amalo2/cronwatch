"""YAML/TOML configuration loader for cronwatch."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

from cronwatch.alerts import AlertDispatcher, LogChannel, SmtpChannel
from cronwatch.job import JobConfig

logger = logging.getLogger(__name__)

_DEFAULTS: dict[str, Any] = {
    "drift_threshold_percent": 20.0,
    "silence_threshold_seconds": 3600,
    "expected_duration_seconds": None,
}


def load_config(path: str | Path) -> tuple[list[JobConfig], AlertDispatcher]:
    """Parse a TOML config file and return job configs + alert dispatcher."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("rb") as fh:
        try:
            raw = tomllib.load(fh)
        except Exception as exc:
            raise ValueError(f"Failed to parse config file {path}: {exc}") from exc

    dispatcher = _build_dispatcher(raw.get("alerts", {}))
    jobs = [_build_job(j) for j in raw.get("jobs", [])]

    logger.info("Loaded %d job(s) from %s", len(jobs), path)
    return jobs, dispatcher


def _build_job(raw: dict[str, Any]) -> JobConfig:
    for required in ("name", "schedule"):
        if required not in raw:
            raise KeyError(f"Job config missing required field: '{required}'")
    return JobConfig(
        name=raw["name"],
        schedule=raw["schedule"],
        command=raw.get("command", ""),
        drift_threshold_percent=float(
            raw.get("drift_threshold_percent", _DEFAULTS["drift_threshold_percent"])
        ),
        silence_threshold_seconds=int(
            raw.get("silence_threshold_seconds", _DEFAULTS["silence_threshold_seconds"])
        ),
        expected_duration_seconds=raw.get(
            "expected_duration_seconds", _DEFAULTS["expected_duration_seconds"]
        ),
    )


def _build_dispatcher(raw: dict[str, Any]) -> AlertDispatcher:
    channels = [LogChannel()]

    smtp_cfg = raw.get("smtp")
    if smtp_cfg:
        for required in ("host", "sender", "recipients"):
            if required not in smtp_cfg:
                raise KeyError(f"SMTP config missing required field: '{required}'")
        channels.append(
            SmtpChannel(
                host=smtp_cfg["host"],
                port=int(smtp_cfg.get("port", 465)),
                sender=smtp_cfg["sender"],
                recipients=smtp_cfg["recipients"],
                username=smtp_cfg.get("username"),
                password=smtp_cfg.get("password"),
                use_tls=smtp_cfg.get("use_tls", True),
            )
        )

    return AlertDispatcher(channels=channels)
