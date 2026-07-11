"""
Clock abstraction. Anything that needs 'now' or 'sleep' goes through
this interface instead of calling time.time()/time.sleep() directly —
lets tests run a rate-limited loop instantly instead of waiting on real
wall-clock time, and lets tests assert exact timing behavior
deterministically.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod


class Clock(ABC):
    @abstractmethod
    def now(self) -> float:
        """Seconds since epoch, monotonic-ish for our purposes."""
        raise NotImplementedError

    @abstractmethod
    def sleep(self, seconds: float) -> None:
        raise NotImplementedError


class RealClock(Clock):
    def now(self) -> float:
        return time.time()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


class FakeClock(Clock):
    """Test double. sleep() just advances the internal clock instead of
    blocking — a loop that 'sleeps' 1000 times runs in microseconds."""

    def __init__(self, start: float = 0.0) -> None:
        self._now = start
        self.sleep_calls: list[float] = []

    def now(self) -> float:
        return self._now

    def sleep(self, seconds: float) -> None:
        self.sleep_calls.append(seconds)
        self._now += seconds

    def advance(self, seconds: float) -> None:
        """Move time forward without going through sleep() — useful for
        simulating 'time passed some other way' in a test."""
        self._now += seconds