"""Prometheus-style metrics exporter for cronwatch job states."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List

from cronwatch.job import JobConfig, JobState


@dataclass
class MetricSample:
    name: str
    labels: Dict[str, str]
    value: float
    timestamp: float = field(default_factory=time.time)

    def to_text(self) -> str:
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(self.labels.items()))
        return f"{self.name}{{{label_str}}} {self.value}"


def collect_metrics(
    configs: Dict[str, JobConfig],
    states: Dict[str, JobState],
) -> List[MetricSample]:
    """Build a list of MetricSamples from current job configs and states."""
    samples: List[MetricSample] = []
    now = time.time()

    for job_id, cfg in configs.items():
        state = states.get(job_id)
        labels = {"job": job_id, "schedule": cfg.schedule}

        last_ts = state.last_execution.timestamp() if (state and state.last_execution) else float("nan")
        samples.append(MetricSample("cronwatch_last_execution_timestamp", labels, last_ts))

        if state and state.last_execution:
            age = now - state.last_execution.timestamp()
        else:
            age = float("nan")
        samples.append(MetricSample("cronwatch_seconds_since_last_execution", labels, age))

        count = len(state.execution_times) if state else 0
        samples.append(MetricSample("cronwatch_execution_count_total", labels, float(count)))

        if state and len(state.execution_times) >= 2:
            diffs = [
                (state.execution_times[i] - state.execution_times[i - 1]).total_seconds()
                for i in range(1, len(state.execution_times))
            ]
            avg_drift = sum(diffs) / len(diffs)
        else:
            avg_drift = float("nan")
        samples.append(MetricSample("cronwatch_avg_interval_seconds", labels, avg_drift))

    return samples


def render_text(samples: List[MetricSample]) -> str:
    """Render samples in a plain-text exposition format."""
    lines: List[str] = []
    seen_names: set = set()
    for s in samples:
        if s.name not in seen_names:
            lines.append(f"# HELP {s.name} cronwatch metric")
            lines.append(f"# TYPE {s.name} gauge")
            seen_names.add(s.name)
        lines.append(s.to_text())
    return "\n".join(lines) + "\n"
