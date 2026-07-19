"""
WindowObserver adapts the existing window-tracking machinery
(WindowInfoSource + change detection) into the new Observer/
ContextEvent plugin architecture. This is the first real proof that
the plugin system replaces the old direct-wiring path (CaptureLoop ->
event_repo.add) rather than sitting unused beside it.

Deliberately reuses WindowInfoSource (capture/types.py) rather than
reimplementing window polling — the OS-access code (Win32 APIs via
WindowsWindowInfoSource) is already correct and tested; this class is
purely an adapter that turns "window changed" into a ContextEvent.

Change detection (is this actually a new window vs. the same one) is
duplicated here from CaptureLoop's run_once() logic deliberately, not
imported — CaptureLoop is being phased toward using PluginRegistry
instead of a single hardcoded WindowInfoSource dependency (see
ARCHITECTURE_STATE.md Day 14 notes), and this observer needs to be
independently correct in the interim rather than depend on
CaptureLoop internals that are mid-refactor.
"""

from __future__ import annotations

from cogn_os.capture.types import WindowInfo, WindowInfoSource
from cogn_os.plugins.events import ContextEvent
from cogn_os.plugins.observer import Observer


class WindowObserver(Observer):
    def __init__(self, source: WindowInfoSource, poll_interval: float = 3.0) -> None:
        self._source = source
        self._poll_interval = poll_interval
        self._last_seen: WindowInfo | None = None

    @property
    def name(self) -> str:
        return "window_tracker"

    @property
    def poll_interval_seconds(self) -> float:
        return self._poll_interval

    def poll(self) -> list[ContextEvent]:
        try:
            info = self._source.get_active_window()
        except Exception:
            return []

        if info is None:
            return []

        changed = self._last_seen is None or (
            info.app_name != self._last_seen.app_name
            or info.window_title != self._last_seen.window_title
        )
        if not changed:
            return []

        self._last_seen = info
        return [
            ContextEvent.now(
                source=self.name,
                event_type="window_changed",
                payload={"app_name": info.app_name, "window_title": info.window_title},
            )
        ]