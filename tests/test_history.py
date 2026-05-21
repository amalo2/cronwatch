"""Tests for cronwatch.history.HistoryStore."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from cronwatch.history import HistoryStore, _serialize_dt, _deserialize_dt

_DT = datetime(2024, 6, 1, 12, 0, 0)


@pytest.fixture()
def store(tmp_path: Path) -> HistoryStore:
    return HistoryStore(path=tmp_path / "history.json")


def test_empty_store_returns_no_history(store: HistoryStore) -> None:
    assert store.get_history("myjob") == []


def test_record_persists_timestamp(store: HistoryStore) -> None:
    store.record("myjob", _DT)
    assert store.get_history("myjob") == [_DT]


def test_multiple_records_ordered(store: HistoryStore) -> None:
    dt1 = datetime(2024, 6, 1, 10, 0, 0)
    dt2 = datetime(2024, 6, 1, 11, 0, 0)
    store.record("myjob", dt1)
    store.record("myjob", dt2)
    assert store.get_history("myjob") == [dt1, dt2]


def test_record_writes_json_to_disk(store: HistoryStore) -> None:
    store.record("myjob", _DT)
    raw = json.loads(store.path.read_text())
    assert "myjob" in raw
    assert raw["myjob"] == ["2024-06-01T12:00:00"]


def test_clear_removes_job_history(store: HistoryStore) -> None:
    store.record("myjob", _DT)
    store.clear("myjob")
    assert store.get_history("myjob") == []


def test_load_reads_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "history.json"
    path.write_text(json.dumps({"backup": ["2024-06-01T08:00:00"]}))
    store = HistoryStore(path=path)
    assert store.get_history("backup") == [datetime(2024, 6, 1, 8, 0, 0)]


def test_corrupt_file_starts_fresh(tmp_path: Path) -> None:
    path = tmp_path / "history.json"
    path.write_text("NOT JSON")
    store = HistoryStore(path=path)  # should not raise
    assert store.get_history("any") == []


def test_serialize_deserialize_roundtrip() -> None:
    assert _deserialize_dt(_serialize_dt(_DT)) == _DT


def test_serialize_none_returns_none() -> None:
    assert _serialize_dt(None) is None
    assert _deserialize_dt(None) is None
