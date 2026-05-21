"""Watcher: ties together config, job state, and drift detection into a runnable loop."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Dict

from cronwatch.config import load_config
from cronwatch.detector import DriftDetector
from cronwatch.job import JobConfig, JobState

logger = logging.getLogger(__name__)


class Watcher:
    """Periodically evaluates all configured jobs for drift or silent failure."""

    def __init__(self, config_path: str, poll_interval: int = 60) -> None:
        self.config_path = config_path
        self.poll_interval = poll_interval

        cfg = load_config(config_path)
        self.jobs: Dict[str, JobConfig] = {j.name: j for j in cfg["jobs"]}
        self.dispatcher = cfg["dispatcher"]
        self._states: Dict[str, JobState] = {
            name: JobState(job_name=name) for name, job in self.jobs.items()
        }
        self._detectors: Dict[str, DriftDetector] = {
            name: DriftDetector(job, self.dispatcher)
            for name, job in self.jobs.items()
        }
        self._running = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_execution(self, job_name: str, duration_seconds: float) -> None:
        """Called externally (e.g. via HTTP hook or IPC) when a job finishes."""
        if job_name not in self.jobs:
            logger.warning("record_execution: unknown job %r", job_name)
            return
        state = self._states[job_name]
        state.record_execution(datetime.now(tz=timezone.utc), duration_seconds)
        logger.info("Recorded execution for %r (%.2fs)", job_name, duration_seconds)

    def check_all(self) -> None:
        """Run drift/silence checks for every job against current time."""
        now = datetime.now(tz=timezone.utc)
        for name, detector in self._detectors.items():
            state = self._states[name]
            detector.check(state, now)

    def run_forever(self) -> None:  # pragma: no cover
        """Block and poll until stopped."""
        self._running = True
        logger.info(
            "Watcher started — %d job(s), poll interval %ds",
            len(self.jobs),
            self.poll_interval,
        )
        try:
            while self._running:
                self.check_all()
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            logger.info("Watcher stopped by keyboard interrupt")
        finally:
            self._running = False

    def stop(self) -> None:  # pragma: no cover
        self._running = False
