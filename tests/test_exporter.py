"""Tests for cronwatch.exporter metrics collection and rendering."""
from __future__ import annotations

import math
from datetime import datetime, timezone

import pytest

from cronwatch.exporter import MetricSample, collect_metrics, render_text
from cronwatch.job import JobConfig, JobState


def _dt(hour: int, minute: int) -> datetime:
    return datetime(2024, 1, 15, hour, minute, tzinfo=timezone.utc)


@pytest.fixture()
def cfg() -> JobConfig:
    return JobConfig(job_id="backup", schedule="0 2 * * *", timeout_seconds=300)


@pytest.fixture()
def empty_state() -> JobState:
    return JobState()


@pytest.fixture()
def state_with_history() -> JobState:
    s = JobState()
    for h in [2, 4, 6]:
        s.record_execution(_dt(h, 0))
    return s


def test_metric_sample_to_text():
    s = MetricSample("my_metric", {"job": "x", "env": "prod"}, 42.0)
    text = s.to_text()
    assert "my_metric" in text
    assert 'env="prod"' in text
    assert 'job="x"' in text
    assert "42.0" in text


def test_collect_metrics_no_state(cfg):
    samples = collect_metrics({"backup": cfg}, {})
    names = {s.name for s in samples}
    assert "cronwatch_last_execution_timestamp" in names
    assert "cronwatch_execution_count_total" in names


def test_collect_metrics_count_zero_without_history(cfg):
    samples = collect_metrics({"backup": cfg}, {})
    count_sample = next(s for s in samples if s.name == "cronwatch_execution_count_total")
    assert count_sample.value == 0.0


def test_collect_metrics_count_reflects_history(cfg, state_with_history):
    samples = collect_metrics({"backup": cfg}, {"backup": state_with_history})
    count_sample = next(s for s in samples if s.name == "cronwatch_execution_count_total")
    assert count_sample.value == 3.0


def test_collect_metrics_avg_interval(cfg, state_with_history):
    samples = collect_metrics({"backup": cfg}, {"backup": state_with_history})
    avg_sample = next(s for s in samples if s.name == "cronwatch_avg_interval_seconds")
    # intervals are all 2 hours = 7200 s
    assert abs(avg_sample.value - 7200.0) < 1.0


def test_collect_metrics_avg_interval_nan_without_enough_history(cfg, empty_state):
    samples = collect_metrics({"backup": cfg}, {"backup": empty_state})
    avg_sample = next(s for s in samples if s.name == "cronwatch_avg_interval_seconds")
    assert math.isnan(avg_sample.value)


def test_render_text_contains_help_and_type(cfg, state_with_history):
    samples = collect_metrics({"backup": cfg}, {"backup": state_with_history})
    text = render_text(samples)
    assert "# HELP" in text
    assert "# TYPE" in text


def test_render_text_ends_with_newline(cfg, state_with_history):
    samples = collect_metrics({"backup": cfg}, {"backup": state_with_history})
    assert render_text(samples).endswith("\n")


def test_render_text_no_duplicate_help_lines(cfg):
    cfg2 = JobConfig(job_id="sync", schedule="*/5 * * * *", timeout_seconds=60)
    samples = collect_metrics({"backup": cfg, "sync": cfg2}, {})
    text = render_text(samples)
    help_lines = [l for l in text.splitlines() if l.startswith("# HELP cronwatch_execution_count_total")]
    assert len(help_lines) == 1
