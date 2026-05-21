"""Tests for cronwatch.reporter."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from cronwatch.job import JobConfig, JobState, ExecutionRecord
from cronwatch.reporter import JobSummary, Reporter


def _dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2024, 1, 15, hour, minute, tzinfo=timezone.utc)


def _make_config(name: str = "backup") -> JobConfig:
    return JobConfig(name=name, schedule="0 2 * * *", command="/usr/bin/backup")


def _make_state(records: list[ExecutionRecord], missed: int = 0) -> JobState:
    state = JobState()
    state.execution_history.extend(records)
    state.missed_count = missed
    return state


# ---------------------------------------------------------------------------
# JobSummary.as_text
# ---------------------------------------------------------------------------

def test_job_summary_as_text_contains_name():
    summary = JobSummary(
        job_name="backup",
        total_executions=5,
        last_execution=_dt(2),
        avg_duration_seconds=12.3,
        missed_count=0,
    )
    text = summary.as_text()
    assert "backup" in text
    assert "12.3s" in text
    assert "executions=5" in text


def test_job_summary_as_text_no_history():
    summary = JobSummary(
        job_name="sync",
        total_executions=0,
        last_execution=None,
        avg_duration_seconds=None,
        missed_count=1,
    )
    text = summary.as_text()
    assert "never" in text
    assert "n/a" in text
    assert "missed=1" in text


# ---------------------------------------------------------------------------
# Reporter.build_summary
# ---------------------------------------------------------------------------

def test_build_summary_returns_none_for_unknown_job():
    reporter = Reporter()
    assert reporter.build_summary("nonexistent") is None


def test_build_summary_with_no_executions():
    config = _make_config()
    state = _make_state([], missed=2)
    reporter = Reporter(jobs={"backup": config}, states={"backup": state})
    summary = reporter.build_summary("backup")
    assert summary is not None
    assert summary.total_executions == 0
    assert summary.last_execution is None
    assert summary.avg_duration_seconds is None
    assert summary.missed_count == 2


def test_build_summary_computes_avg_duration():
    records = [
        ExecutionRecord(timestamp=_dt(2), duration_seconds=10.0),
        ExecutionRecord(timestamp=_dt(3), duration_seconds=20.0),
    ]
    config = _make_config()
    state = _make_state(records)
    reporter = Reporter(jobs={"backup": config}, states={"backup": state})
    summary = reporter.build_summary("backup")
    assert summary is not None
    assert summary.avg_duration_seconds == pytest.approx(15.0)
    assert summary.total_executions == 2
    assert summary.last_execution == _dt(3)


# ---------------------------------------------------------------------------
# Reporter.report_all
# ---------------------------------------------------------------------------

def test_report_all_returns_all_summaries():
    jobs = {
        "job_a": _make_config("job_a"),
        "job_b": _make_config("job_b"),
    }
    states = {
        "job_a": _make_state([ExecutionRecord(timestamp=_dt(1), duration_seconds=5.0)]),
        "job_b": _make_state([]),
    }
    reporter = Reporter(jobs=jobs, states=states)
    summaries = reporter.report_all()
    assert len(summaries) == 2
    names = {s.job_name for s in summaries}
    assert names == {"job_a", "job_b"}


def test_report_all_logs_each_summary(caplog):
    import logging
    jobs = {"myjob": _make_config("myjob")}
    states = {"myjob": _make_state([])}
    reporter = Reporter(jobs=jobs, states=states)
    with caplog.at_level(logging.INFO, logger="cronwatch.reporter"):
        reporter.report_all()
    assert any("myjob" in rec.message for rec in caplog.records)
