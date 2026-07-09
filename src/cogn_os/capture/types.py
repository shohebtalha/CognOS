"""
Core capture types. The WindowInfoSource interface is the seam between
"how do we ask the OS what window is focused" and "everything else" —
the poll loop, tests, and future macOS/Linux backends all depend on this
interface, never on a concrete OS implementation directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class WindowInfo:
    """A snapshot of the currently focused window at a point in time."""

    app_name: str
    window_title: str
    captured_at: datetime

    @classmethod
    def now(cls, app_name: str, window_title: str) -> "WindowInfo":
        return cls(app_name=app_name, window_title=window_title, captured_at=datetime.now(timezone.utc))


class WindowInfoSource(ABC):
    """Abstraction over 'what window is focused right now'.

    Concrete implementations talk to the OS (Win32 APIs, Quartz, X11).
    Tests use a fake implementation instead, so capture-loop logic can be
    verified without touching real windows or running on a specific OS.
    """

    @abstractmethod
    def get_active_window(self) -> WindowInfo | None:
        """Return info about the focused window, or None if it can't be
        determined (e.g. no window focused, permissions denied)."""
        raise NotImplementedError