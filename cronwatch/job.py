"""Data model for a monitored cron job."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from cronwatch.schedule import CronSchedule


@dataclass
class JobConfig:
    """Static configuration for a monitored job."""

    name: str
    schedule: str
    grace_seconds: int = 120
    timeout_seconds: Optional[int] = None

    def __post_init__(self) -> None:
        # Validate the schedule at construction time
        self._parsed_schedule = CronSchedule(self.schedule)

    @property
    def parsed_schedule(self) -> CronSchedule:
        return self._parsed_schedule


@dataclass
class JobState:
    """Runtime state tracked for a monitored job."""

    config: JobConfig
    last_seen: Optional[datetime] = None
    last_duration_seconds: Optional[float] = None
    failure_count: int = 0
    alerts_sent: int = 0

    def record_execution(self, started_at: datetime, duration_seconds: float) -> None:
        """Update state after a successful execution ping."""
        self.last_seen = started_at
        self.last_duration_seconds = duration_seconds
        self.failure_count = 0

    def is_overdue(self, now: Optional[datetime] = None) -> bool:
        """Return True if the job has not reported within the grace window."""
        if now is None:
            now = datetime.now(tz=timezone.utc)
        if self.last_seen is None:
            return False  # never seen — handled separately
        elapsed = (now - self.last_seen).total_seconds()
        return elapsed > self.config.grace_seconds

    def is_timed_out(self) -> bool:
        """Return True if the last execution exceeded the configured timeout."""
        if self.config.timeout_seconds is None or self.last_duration_seconds is None:
            return False
        return self.last_duration_seconds > self.config.timeout_seconds

    def __repr__(self) -> str:
        return (
            f"JobState(name={self.config.name!r}, last_seen={self.last_seen}, "
            f"failure_count={self.failure_count})"
        )
