"""Parse and evaluate cron schedule expressions."""

import re
from datetime import datetime, timezone
from typing import Optional

CRON_FIELDS = ["minute", "hour", "day", "month", "weekday"]


class CronSchedule:
    """Represents a parsed cron schedule and can compute expected run times."""

    def __init__(self, expression: str) -> None:
        self.expression = expression.strip()
        self._fields = self._parse(self.expression)

    def _parse(self, expression: str) -> dict:
        parts = expression.split()
        if len(parts) != 5:
            raise ValueError(
                f"Invalid cron expression '{expression}': expected 5 fields, got {len(parts)}"
            )
        return dict(zip(CRON_FIELDS, parts))

    def _field_matches(self, field: str, value: int, min_val: int, max_val: int) -> bool:
        if field == "*":
            return True
        for part in field.split(","):
            if "/" in part:
                base, step = part.split("/", 1)
                start = min_val if base == "*" else int(base)
                if value >= start and (value - start) % int(step) == 0:
                    return True
            elif "-" in part:
                lo, hi = part.split("-", 1)
                if int(lo) <= value <= int(hi):
                    return True
            elif int(part) == value:
                return True
        return False

    def matches(self, dt: Optional[datetime] = None) -> bool:
        """Return True if the given datetime matches this schedule."""
        if dt is None:
            dt = datetime.now(tz=timezone.utc)
        return (
            self._field_matches(self._fields["minute"], dt.minute, 0, 59)
            and self._field_matches(self._fields["hour"], dt.hour, 0, 23)
            and self._field_matches(self._fields["day"], dt.day, 1, 31)
            and self._field_matches(self._fields["month"], dt.month, 1, 12)
            and self._field_matches(self._fields["weekday"], dt.weekday(), 0, 6)
        )

    def __repr__(self) -> str:
        return f"CronSchedule({self.expression!r})"
