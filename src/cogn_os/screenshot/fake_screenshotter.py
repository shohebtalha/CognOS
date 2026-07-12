"""
Test double for Screenshotter — returns a scripted Screenshot (or None)
without touching the real screen. Mirrors FakeWindowInfoSource in the
capture package.
"""

from __future__ import annotations

from cogn_os.screenshot.types import Screenshot, Screenshotter


class FakeScreenshotter(Screenshotter):
    def __init__(self, screenshot: Screenshot | None = None) -> None:
        self._screenshot = screenshot
        self.call_count = 0

    def capture(self) -> Screenshot | None:
        self.call_count += 1
        return self._screenshot

    def set_next(self, screenshot: Screenshot | None) -> None:
        self._screenshot = screenshot