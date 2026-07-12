"""
Screenshot domain types. Same pattern as capture/types.py: an interface
(Screenshotter) that concrete implementations satisfy, so the rest of
the app — and every test — depends on this abstraction, never on PIL or
the OS screen-grab API directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class Screenshot:
    """An encoded screenshot ready to send over the wire (base64 JPEG)
    or store. Keeping raw bytes + a base64 cache separate would be a
    premature optimization here — base64 is what every downstream
    consumer (Anthropic API, disk cache) actually wants."""

    image_b64: str
    width: int
    height: int
    captured_at: datetime
    format: str = "jpeg"

    @classmethod
    def now(cls, image_b64: str, width: int, height: int, format: str = "jpeg") -> "Screenshot":
        return cls(
            image_b64=image_b64,
            width=width,
            height=height,
            captured_at=datetime.now(timezone.utc),
            format=format,
        )


class Screenshotter(ABC):
    @abstractmethod
    def capture(self) -> Screenshot | None:
        """Capture the primary display. Returns None if capture fails
        (e.g. permissions, headless environment) — callers must handle
        this gracefully, same contract as WindowInfoSource.get_active_window."""
        raise NotImplementedError