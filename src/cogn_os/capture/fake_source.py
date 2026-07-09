"""
Test double for WindowInfoSource. Feed it a scripted sequence of
WindowInfo (or None) values and it plays them back one per call —
lets capture-loop tests run deterministically with zero OS dependency.
"""

from __future__ import annotations

from collections.abc import Iterable

from cogn_os.capture.types import WindowInfo, WindowInfoSource


class FakeWindowInfoSource(WindowInfoSource):
    def __init__(self, sequence: Iterable[WindowInfo | None]) -> None:
        self._sequence = list(sequence)
        self._index = 0
        self.call_count = 0

    def get_active_window(self) -> WindowInfo | None:
        self.call_count += 1
        if self._index >= len(self._sequence):
            return self._sequence[-1] if self._sequence else None
        value = self._sequence[self._index]
        self._index += 1
        return value