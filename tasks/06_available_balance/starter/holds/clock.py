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


class ManualClock:
    """Settable clock for local development and demos; time only moves when advance() is called."""

    def __init__(self, start):
        if start.utcoffset() is None:
            raise ValueError("aware start required")
        self._now = start

    def now(self):
        return self._now

    def advance(self, delta):
        self._now = self._now + delta
        return self._now
