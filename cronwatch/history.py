"""Persistent execution history storage for cronwatch jobs."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

log = logging.getLogger(__name__)

DEFAULT_HISTORY_PATH = Path("/var/lib/cronwatch/history.json")
_DT_FMT = "%Y-%m-%dT%H:%M:%S"


def _serialize_dt(dt: Optional[datetime]) -> Optional[str]:
    return dt.strftime(_DT_FMT) if dt is not None else None


def _deserialize_dt(s: Optional[str]) -> Optional[datetime]:
    return datetime.strptime(s, _DT_FMT) if s is not None else None


class HistoryStore:
    """Load and persist per-job execution timestamps to a JSON file."""

    def __init__(self, path: Path = DEFAULT_HISTORY_PATH) -> None:
        self.path = Path(path)
        self._data: Dict[str, List[str]] = {}
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record(self, job_name: str, executed_at: datetime) -> None:
        """Append *executed_at* for *job_name* and flush to disk."""
        bucket = self._data.setdefault(job_name, [])
        bucket.append(_serialize_dt(executed_at))  # type: ignore[arg-type]
        self._save()

    def get_history(self, job_name: str) -> List[datetime]:
        """Return stored execution timestamps (oldest first)."""
        return [_deserialize_dt(s) for s in self._data.get(job_name, [])]  # type: ignore[misc]

    def clear(self, job_name: str) -> None:
        """Remove all history for *job_name* and flush."""
        self._data.pop(job_name, None)
        self._save()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self.path.exists():
            log.debug("History file %s not found; starting fresh.", self.path)
            return
        try:
            with self.path.open() as fh:
                self._data = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("Could not load history from %s: %s", self.path, exc)
            self._data = {}

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            with tmp.open("w") as fh:
                json.dump(self._data, fh, indent=2)
            os.replace(tmp, self.path)
        except OSError as exc:
            log.error("Could not save history to %s: %s", self.path, exc)
