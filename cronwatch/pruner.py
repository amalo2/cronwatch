"""History pruning utilities — keep only recent executions per job."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import List

from cronwatch.history import HistoryStore

log = logging.getLogger(__name__)

DEFAULT_MAX_ENTRIES = 100
DEFAULT_MAX_AGE_DAYS = 30


def prune_by_count(store: HistoryStore, job_name: str, max_entries: int = DEFAULT_MAX_ENTRIES) -> int:
    """Keep only the *max_entries* most recent timestamps. Returns number removed."""
    history: List[datetime] = store.get_history(job_name)
    if len(history) <= max_entries:
        return 0
    removed = len(history) - max_entries
    store._data[job_name] = store._data[job_name][-max_entries:]  # type: ignore[index]
    store._save()
    log.debug("Pruned %d old entries for job '%s' (count limit).", removed, job_name)
    return removed


def prune_by_age(store: HistoryStore, job_name: str, max_age_days: int = DEFAULT_MAX_AGE_DAYS, now: datetime | None = None) -> int:
    """Remove timestamps older than *max_age_days*. Returns number removed."""
    cutoff = (now or datetime.utcnow()) - timedelta(days=max_age_days)
    history: List[datetime] = store.get_history(job_name)
    fresh = [dt for dt in history if dt >= cutoff]
    removed = len(history) - len(fresh)
    if removed:
        store._data[job_name] = [dt.strftime("%Y-%m-%dT%H:%M:%S") for dt in fresh]  # type: ignore[index]
        store._save()
        log.debug("Pruned %d stale entries for job '%s' (age limit).", removed, job_name)
    return removed


def prune_all(store: HistoryStore, max_entries: int = DEFAULT_MAX_ENTRIES, max_age_days: int = DEFAULT_MAX_AGE_DAYS) -> None:
    """Run both pruning strategies across every job in *store*."""
    now = datetime.utcnow()
    for job_name in list(store._data.keys()):  # type: ignore[attr-defined]
        prune_by_age(store, job_name, max_age_days=max_age_days, now=now)
        prune_by_count(store, job_name, max_entries=max_entries)
