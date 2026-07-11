"""
The capture loop doesn't know or care what happens when a window change
is detected — it just calls a callback. This keeps the loop reusable:
Day 3 wires it to storage only, Day 6+ adds the reasoning callback,
without ever touching loop internals again.
"""

from __future__ import annotations

from typing import Protocol

from cogn_os.capture.types import WindowInfo


class OnWindowChanged(Protocol):
    def __call__(self, info: WindowInfo) -> None: ...