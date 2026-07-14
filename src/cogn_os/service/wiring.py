"""
Assembles a CaptureLoop wired to storage AND the ML suggestion gate.
This replaces Day 3's storage-only wiring: every window change is still
logged (unconditionally, for the timeline), but now also runs through
FeatureExtractor -> SuggestionGate to decide whether it's flag-worthy.
The actual "what happens when flagged" (LLM call, notification) is
still a separate callback, wired in Day 12+ — this function's job stops
at "was this worth flagging," keeping single responsibility intact.
"""

from __future__ import annotations

import logging
from typing import Protocol

from cogn_os.capture.types import WindowInfo, WindowInfoSource
from cogn_os.config import Settings
from cogn_os.ml.context_tracker import ContextTracker
from cogn_os.ml.feature_extractor import FeatureExtractor
from cogn_os.ml.suggestion_gate import SuggestionGate
from cogn_os.service.capture_loop import CaptureLoop
from cogn_os.service.clock import Clock
from cogn_os.storage.repository import EventRepository

logger = logging.getLogger(__name__)


class OnFlagged(Protocol):
    def __call__(self, info: WindowInfo) -> None: ...


def build_storage_backed_loop(
    settings: Settings,
    source: WindowInfoSource,
    clock: Clock,
    event_repo: EventRepository,
) -> CaptureLoop:
    """Day 3's original wiring — storage only, no ML. Kept for
    backwards compatibility / simpler debugging when the ML gate isn't
    needed (e.g. pure timeline logging)."""
    return CaptureLoop(
        source=source,
        clock=clock,
        poll_interval_seconds=settings.poll_interval_seconds,
        excluded_apps=settings.excluded_apps,
        on_window_changed=event_repo.add,
    )


def build_ml_gated_loop(
    settings: Settings,
    source: WindowInfoSource,
    clock: Clock,
    event_repo: EventRepository,
    suggestion_gate: SuggestionGate,
    on_flagged: OnFlagged,
    context_tracker: ContextTracker | None = None,
    feature_extractor: FeatureExtractor | None = None,
) -> CaptureLoop:
    """Every window change: always logged to storage; additionally run
    through FeatureExtractor -> SuggestionGate, and on_flagged() fires
    only if the gate says yes."""
    tracker = context_tracker or ContextTracker()
    extractor = feature_extractor or FeatureExtractor()

    def on_window_changed(info: WindowInfo) -> None:
        event_repo.add(info)

        features = extractor.extract(
            current=info,
            previous=tracker.previous,
            history=tracker.history,
            last_llm_call_at=tracker.last_llm_call_at,
            apps_seen_today=tracker.apps_seen_today,
        )
        tracker.record_event(info)
        tracker.set_previous(info)

        try:
            flagged = suggestion_gate.should_flag(features)
        except Exception:
            logger.exception("suggestion gate failed; treating as not-flagged")
            flagged = False

        if flagged:
            tracker.record_llm_call(info.captured_at)
            on_flagged(info)

    return CaptureLoop(
        source=source,
        clock=clock,
        poll_interval_seconds=settings.poll_interval_seconds,
        excluded_apps=settings.excluded_apps,
        on_window_changed=on_window_changed,
    )