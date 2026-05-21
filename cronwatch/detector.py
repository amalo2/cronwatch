"""Drift and silent-failure detection logic for cronwatch."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from cronwatch.alerts import AlertDispatcher, AlertEvent
from cronwatch.job import JobConfig, JobState

logger = logging.getLogger(__name__)


class DriftDetector:
    """Detects execution-time drift and silent failures for a single job."""

    def __init__(
        self,
        config: JobConfig,
        state: JobState,
        dispatcher: AlertDispatcher,
    ) -> None:
        self.config = config
        self.state = state
        self.dispatcher = dispatcher

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self, now: Optional[datetime] = None) -> None:
        """Run all checks against the current state."""
        now = now or datetime.utcnow()
        self._check_silent_failure(now)
        self._check_drift()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_silent_failure(self, now: datetime) -> None:
        """Alert if the job has not run within its expected window."""
        if self.state.last_run_at is None:
            return  # No history yet; skip.

        grace = timedelta(seconds=self.config.silence_threshold_seconds)
        overdue_by = now - (self.state.last_run_at + grace)
        if overdue_by.total_seconds() > 0:
            self.dispatcher.dispatch(
                AlertEvent(
                    job_name=self.config.name,
                    kind="silent_failure",
                    message=(
                        f"Job '{self.config.name}' has not run for "
                        f"{int(overdue_by.total_seconds())}s beyond its threshold "
                        f"of {self.config.silence_threshold_seconds}s."
                    ),
                    severity="critical",
                    extra={"overdue_seconds": overdue_by.total_seconds()},
                )
            )

    def _check_drift(self) -> None:
        """Alert if recent execution durations deviate from the baseline."""
        durations = self.state.recent_durations
        if len(durations) < 2:
            return

        baseline = self.config.expected_duration_seconds
        if baseline is None:
            baseline = durations[0]

        latest = durations[-1]
        drift_pct = abs(latest - baseline) / baseline * 100 if baseline else 0

        threshold_pct = self.config.drift_threshold_percent
        if drift_pct > threshold_pct:
            severity = "critical" if drift_pct > threshold_pct * 2 else "warning"
            self.dispatcher.dispatch(
                AlertEvent(
                    job_name=self.config.name,
                    kind="drift",
                    message=(
                        f"Job '{self.config.name}' duration drifted {drift_pct:.1f}% "
                        f"(latest={latest:.2f}s, baseline={baseline:.2f}s)."
                    ),
                    severity=severity,
                    extra={"drift_percent": drift_pct, "latest": latest, "baseline": baseline},
                )
            )
