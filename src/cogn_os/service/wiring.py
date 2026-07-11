"""
Assembles a CaptureLoop that logs every non-excluded window change to
the EventRepository. This is the first real "production" wiring — later
days add the reasoning callback alongside this one without changing
this function's shape.
"""

from __future__ import annotations

from cogn_os.capture.types import WindowInfoSource
from cogn_os.config import Settings
from cogn_os.service.capture_loop import CaptureLoop
from cogn_os.service.clock import Clock
from cogn_os.storage.repository import EventRepository


def build_storage_backed_loop(
    settings: Settings,
    source: WindowInfoSource,
    clock: Clock,
    event_repo: EventRepository,
) -> CaptureLoop:
    return CaptureLoop(
        source=source,
        clock=clock,
        poll_interval_seconds=settings.poll_interval_seconds,
        excluded_apps=settings.excluded_apps,
        on_window_changed=event_repo.add,
    )