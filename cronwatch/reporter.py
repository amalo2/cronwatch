"""Periodic summary reporter for cronwatch job states."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from cronwatch.job import JobConfig, JobState

logger = logging.getLogger(__name__)


@dataclass
class JobSummary:
    """Summary statistics for a single monitored job."""

    job_name: str
    total_executions: int
    last_execution: Optional[datetime]
    avg_duration_seconds: Optional[float]
    missed_count: int

    def as_text(self) -> str:
        last = self.last_execution.isoformat() if self.last_execution else "never"
        avg = (
            f"{self.avg_duration_seconds:.1f}s"
            if self.avg_duration_seconds is not None
            else "n/a"
        )
        return (
            f"[{self.job_name}] executions={self.total_executions} "
            f"last={last} avg_duration={avg} missed={self.missed_count}"
        )


@dataclass
class Reporter:
    """Generates and logs summary reports for all tracked jobs."""

    jobs: Dict[str, JobConfig] = field(default_factory=dict)
    states: Dict[str, JobState] = field(default_factory=dict)

    def build_summary(self, job_name: str) -> Optional[JobSummary]:
        """Build a JobSummary for the named job, or None if unknown."""
        config = self.jobs.get(job_name)
        state = self.states.get(job_name)
        if config is None or state is None:
            return None

        history = state.execution_history
        total = len(history)
        last_exec = history[-1].timestamp if history else None

        durations = [
            e.duration_seconds for e in history if e.duration_seconds is not None
        ]
        avg_duration = sum(durations) / len(durations) if durations else None

        return JobSummary(
            job_name=job_name,
            total_executions=total,
            last_execution=last_exec,
            avg_duration_seconds=avg_duration,
            missed_count=state.missed_count,
        )

    def report_all(self) -> List[JobSummary]:
        """Build and log summaries for every registered job."""
        summaries: List[JobSummary] = []
        for name in self.jobs:
            summary = self.build_summary(name)
            if summary:
                logger.info("cronwatch report: %s", summary.as_text())
                summaries.append(summary)
        return summaries
