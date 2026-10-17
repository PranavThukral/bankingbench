"""Declared application clock boundary."""
from datetime import datetime, timezone
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        ...


class SystemClock:
    def now(self):
        return datetime.now(timezone.utc)


def instant(clock):
    result = clock.now()
    if result.utcoffset() is None:
        raise ValueError("aware clock required")
    return result.timestamp()
