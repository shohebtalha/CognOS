"""
Turns raw event history (from EventRepository) into a SuggestionFeatures
vector for the *current* event. This is the seam between storage and
ML — it depends on the EventRepository interface from storage/, never
on a concrete database, so it's fully unit-testable with an in-memory
list of events.

As of Day 10, also depends on SemanticChangeDetector to compute title
similarity to the previous event — this is genuinely optional (passed
as None when unavailable, e.g. very early tests) so this class doesn't
force every caller to load a PyTorch model just to extract features.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from cogn_os.capture.types import WindowInfo
from cogn_os.embeddings.change_detector import SemanticChangeDetector
from cogn_os.ml.app_category import categorize
from cogn_os.ml.features import SuggestionFeatures


class FeatureExtractor:
    def __init__(
        self,
        rolling_window: timedelta = timedelta(minutes=5),
        change_detector: SemanticChangeDetector | None = None,
    ) -> None:
        self._rolling_window = rolling_window
        self._change_detector = change_detector

    def extract(
        self,
        current: WindowInfo,
        previous: WindowInfo | None,
        history: list[WindowInfo],
        last_llm_call_at: datetime | None,
        apps_seen_today: set[str],
    ) -> SuggestionFeatures:
        seconds_since_last_call = (
            float("inf")
            if last_llm_call_at is None
            else (current.captured_at - last_llm_call_at).total_seconds()
        )

        app_changed = previous is None or current.app_name != previous.app_name

        window_start = current.captured_at - self._rolling_window
        switches_last_5min = sum(1 for e in history if e.captured_at >= window_start)

        if self._change_detector is not None:
            previous_title = previous.window_title if previous is not None else None
            decision = self._change_detector.compare(previous_title, current.window_title)
            title_similarity = decision.similarity
        else:
            # No detector wired up (e.g. lightweight tests that don't
            # need embeddings) — neutral midpoint value rather than 0,
            # since 0 would falsely signal "completely different."
            title_similarity = 0.5

        return SuggestionFeatures(
            seconds_since_last_llm_call=seconds_since_last_call,
            hour_of_day=current.captured_at.hour,
            is_weekend=current.captured_at.weekday() >= 5,
            app_category=categorize(current.app_name),
            title_length=len(current.window_title),
            app_changed=app_changed,
            is_first_time_app_today=current.app_name not in apps_seen_today,
            switches_last_5min=switches_last_5min,
            title_semantic_similarity_to_previous=title_similarity,
        )