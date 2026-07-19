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
from cogn_os.storage.repository import EventRepository, FeatureLogRepository

from cogn_os.context.privacy_filter import is_sensitive



logger = logging.getLogger(__name__)


class OnFlagged(Protocol):
    def __call__(self, info: WindowInfo, history: list[WindowInfo]) -> None: ...
def build_ml_gated_loop(
    settings: Settings,
    source: WindowInfoSource,
    clock: Clock,
    event_repo: EventRepository,
    suggestion_gate: SuggestionGate,
    on_flagged: OnFlagged,
    feature_log_repo: FeatureLogRepository | None = None,
    context_tracker: ContextTracker | None = None,
    feature_extractor: FeatureExtractor | None = None,
) -> CaptureLoop:
    tracker = context_tracker or ContextTracker()
    extractor = feature_extractor or FeatureExtractor()

    def on_window_changed(info: WindowInfo) -> None:
        if is_sensitive(info):
            # Sensitive content never gets logged, feature-extracted,
            # or reasoned about at all — the strongest point to enforce
            # this, before any downstream storage or processing.
            return
        event_repo.add(info)

        features = extractor.extract(
            current=info, previous=tracker.previous, history=tracker.history,
            last_llm_call_at=tracker.last_llm_call_at, apps_seen_today=tracker.apps_seen_today,
        )
        tracker.record_event(info)
        tracker.set_previous(info)

        try:
            model_says_flag = suggestion_gate.should_flag(features)
        except Exception:
            logger.exception("suggestion gate failed; treating as not-flagged")
            model_says_flag = False

        # Hard cooldown floor, independent of the model's raw decision.
        # Without this, a model that flags frequently resets
        # last_llm_call_at on nearly every event, collapsing
        # seconds_since_last_llm_call toward zero — a feedback loop that
        # pushes live feature values far outside the training
        # distribution (found via live testing, Day 11). The ML gate
        # decides WHETHER a moment looks interesting; this cooldown
        # decides whether we're ALLOWED to act on that right now.
        cooldown_elapsed = (
            tracker.last_llm_call_at is None
            or (info.captured_at - tracker.last_llm_call_at).total_seconds() >= settings.min_seconds_between_llm_calls
        )
        flagged = model_says_flag and cooldown_elapsed

        if feature_log_repo is not None:
            probability = getattr(suggestion_gate, "predict_probability", lambda f: float(model_says_flag))(features)
            fdict = features.to_dict()
            fdict["app_category"] = fdict["app_category"].value
            feature_log_repo.add(info, fdict, probability=probability, flagged=flagged)

        if flagged:
            tracker.record_llm_call(info.captured_at)
            on_flagged(info, tracker.history)

    return CaptureLoop(
        source=source, clock=clock, poll_interval_seconds=settings.poll_interval_seconds,
        excluded_apps=settings.excluded_apps, on_window_changed=on_window_changed,
    )

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