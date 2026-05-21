"""Tests for cronwatch.pruner pruning utilities."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from cronwatch.history import HistoryStore
from cronwatch.pruner import prune_by_count, prune_by_age, prune_all

_NOW = datetime(2024, 6, 15, 12, 0, 0)


@pytest.fixture()
def store(tmp_path: Path) -> HistoryStore:
    return HistoryStore(path=tmp_path / "history.json")


def _fill(store: HistoryStore, job: str, count: int, base: datetime = _NOW) -> None:
    for i in range(count):
        store.record(job, base - timedelta(hours=count - i))


def test_prune_by_count_removes_oldest(store: HistoryStore) -> None:
    _fill(store, "job", 10)
    removed = prune_by_count(store, "job", max_entries=5)
    assert removed == 5
    assert len(store.get_history("job")) == 5


def test_prune_by_count_no_op_when_under_limit(store: HistoryStore) -> None:
    _fill(store, "job", 3)
    removed = prune_by_count(store, "job", max_entries=10)
    assert removed == 0
    assert len(store.get_history("job")) == 3


def test_prune_by_age_removes_old_entries(store: HistoryStore) -> None:
    old = _NOW - timedelta(days=40)
    recent = _NOW - timedelta(days=5)
    store.record("job", old)
    store.record("job", recent)
    removed = prune_by_age(store, "job", max_age_days=30, now=_NOW)
    assert removed == 1
    history = store.get_history("job")
    assert history == [recent]


def test_prune_by_age_keeps_all_when_fresh(store: HistoryStore) -> None:
    _fill(store, "job", 5, base=_NOW)
    removed = prune_by_age(store, "job", max_age_days=30, now=_NOW)
    assert removed == 0


def test_prune_all_applies_to_every_job(store: HistoryStore) -> None:
    for name in ("job_a", "job_b"):
        _fill(store, name, 20)
    prune_all(store, max_entries=10, max_age_days=365)
    assert len(store.get_history("job_a")) == 10
    assert len(store.get_history("job_b")) == 10


def test_prune_by_count_keeps_most_recent(store: HistoryStore) -> None:
    base = datetime(2024, 1, 1)
    timestamps = [base + timedelta(hours=i) for i in range(8)]
    for dt in timestamps:
        store.record("job", dt)
    prune_by_count(store, "job", max_entries=3)
    assert store.get_history("job") == timestamps[-3:]
