"""
PluginRegistry owns a collection of Observer instances and is
responsible for calling poll() on each at its own configured interval,
collecting every ContextEvent produced into a single stream. This is
the component that turns N independent plugins into "one AI for the
OS" — the reasoning engine downstream only ever sees the merged
ContextEvent stream, never individual plugins.

Key design decision: a single misbehaving observer must never take
down the others. Observer.poll() is documented to never raise, but the
registry does not trust that contract blindly — every poll() call is
wrapped in its own try/except, so a buggy or crashing plugin degrades
to "stops producing events" rather than crashing the whole runtime.

Uses the existing Clock abstraction (service/clock.py) for the same
testability reason as CaptureLoop — poll_all() can be driven
deterministically in tests via FakeClock instead of real sleeps.
"""

from __future__ import annotations

import logging

from cogn_os.plugins.events import ContextEvent
from cogn_os.plugins.observer import Observer
from cogn_os.service.clock import Clock

logger = logging.getLogger(__name__)


class PluginRegistry:
    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._observers: dict[str, Observer] = {}
        self._last_polled_at: dict[str, float] = {}

    def register(self, observer: Observer) -> None:
        if observer.name in self._observers:
            raise ValueError(f"an observer named {observer.name!r} is already registered")
        self._observers[observer.name] = observer
        self._last_polled_at[observer.name] = 0.0

    def unregister(self, name: str) -> None:
        self._observers.pop(name, None)
        self._last_polled_at.pop(name, None)

    @property
    def registered_names(self) -> list[str]:
        return list(self._observers.keys())

    def poll_all(self, force: bool = False) -> list[ContextEvent]:
        """Poll every registered observer whose interval has elapsed
        (or all of them, if force=True — used for tests/manual runs).
        Never raises, regardless of what individual observers do."""
        now = self._clock.now()
        all_events: list[ContextEvent] = []

        for name, observer in self._observers.items():
            elapsed = now - self._last_polled_at[name]
            if not force and elapsed < observer.poll_interval_seconds:
                continue

            try:
                events = observer.poll()
                all_events.extend(events)
            except Exception:
                logger.exception("observer %r raised during poll(); skipping this cycle", name)
            finally:
                self._last_polled_at[name] = now

        return all_events