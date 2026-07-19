"""
Test double for Observer — returns a scripted sequence of ContextEvent
lists, one batch per poll() call. Mirrors FakeWindowInfoSource /
FakeClock / etc. throughout this codebase.
"""

from __future__ import annotations

from cogn_os.plugins.events import ContextEvent
from cogn_os.plugins.observer import Observer


class FakeObserver(Observer):
    def __init__(self, plugin_name: str, batches: list[list[ContextEvent]], poll_interval: float = 5.0) -> None:
        self._name = plugin_name
        self._batches = batches
        self._index = 0
        self._poll_interval = poll_interval
        self.poll_call_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def poll_interval_seconds(self) -> float:
        return self._poll_interval

    def poll(self) -> list[ContextEvent]:
        self.poll_call_count += 1
        if self._index >= len(self._batches):
            return []
        batch = self._batches[self._index]
        self._index += 1
        return batch


class ExplodingObserver(Observer):
    """Deliberately misbehaving observer for testing that the registry
    survives a plugin that violates the 'never raise' contract."""

    def __init__(self, plugin_name: str = "exploding") -> None:
        self._name = plugin_name

    @property
    def name(self) -> str:
        return self._name

    def poll(self) -> list[ContextEvent]:
        raise RuntimeError("this plugin is broken")