"""
The core polling loop. Deliberately dumb: poll -> detect change -> filter
-> callback -> sleep -> repeat. All the "what do we do about it" logic
lives in the callback(s) passed in, not here. run_once() is exposed
separately from run() so tests can drive the loop one tick at a time
without needing threads or real time.
"""

from __future__ import annotations

import logging

from cogn_os.capture.types import WindowInfo, WindowInfoSource
from cogn_os.service.clock import Clock
from cogn_os.service.events import OnWindowChanged
from cogn_os.service.filters import is_excluded

logger = logging.getLogger(__name__)


class CaptureLoop:
    def __init__(
        self,
        source: WindowInfoSource,
        clock: Clock,
        poll_interval_seconds: float,
        excluded_apps: frozenset[str],
        on_window_changed: OnWindowChanged,
    ) -> None:
        self._source = source
        self._clock = clock
        self._poll_interval_seconds = poll_interval_seconds
        self._excluded_apps = excluded_apps
        self._on_window_changed = on_window_changed

        self._last_seen: WindowInfo | None = None
        self._running = False
        self.tick_count = 0

    def run_once(self) -> None:
        """Perform exactly one poll cycle. Public so tests (and a
        supervising loop) can step through deterministically."""
        self.tick_count += 1
        info = self._source.get_active_window()
        if info is None:
            return

        changed = self._last_seen is None or (
            info.app_name != self._last_seen.app_name
            or info.window_title != self._last_seen.window_title
        )
        if not changed:
            return

        self._last_seen = info

        if is_excluded(info, self._excluded_apps):
            logger.debug("skipping excluded app: %s", info.app_name)
            return

        self._on_window_changed(info)

    def run(self, max_ticks: int | None = None) -> None:
        """Run continuously until stop() is called (or max_ticks reached,
        used only in tests — production callers never pass it)."""
        self._running = True
        ticks = 0
        while self._running:
            self.run_once()
            ticks += 1
            if max_ticks is not None and ticks >= max_ticks:
                break
            self._clock.sleep(self._poll_interval_seconds)

    def stop(self) -> None:
        self._running = False