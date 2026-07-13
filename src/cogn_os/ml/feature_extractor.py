"""
Turns raw event history (from EventRepository) into a SuggestionFeatures
vector for the *current* event. This is the seam between storage and
ML — it depends on the EventRepository interface from storage/, never
on a concrete database, so it's fully unit-testable with an in-memory
list of events.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from cogn_os.capture.types import WindowInfo
from cogn_os.ml.app_category import categorize
from cogn_os.ml.features import SuggestionFeatures


class FeatureExtractor:
    def __init__(self, rolling_window: timedelta = timedelta(minutes=5)) -> None:
        self._rolling_window = rolling_window

    def extract(
        self,
        current: WindowInfo,
        previous: WindowInfo | None,
        history: list[WindowInfo],
        last_llm_call_at: datetime | None,
        apps_seen_today: set[str],
    ) -> SuggestionFeatures:
        """
        current: the event we're deciding whether to flag
        previous: the event immediately before it (may be None on the very first event)
        history: recent events (chronological, oldest first) used for the rolling-switch count
        last_llm_call_at: timestamp of the most recent LLM call, or None if never called
        apps_seen_today: set of app_names already observed today, used for novelty detection
        """
        seconds_since_last_call = (
            float("inf")
            if last_llm_call_at is None
            else (current.captured_at - last_llm_call_at).total_seconds()
        )

        app_changed = previous is None or current.app_name != previous.app_name

        window_start = current.captured_at - self._rolling_window
        switches_last_5min = sum(1 for e in history if e.captured_at >= window_start)

        return SuggestionFeatures(
            seconds_since_last_llm_call=seconds_since_last_call,
            hour_of_day=current.captured_at.hour,
            is_weekend=current.captured_at.weekday() >= 5,
            app_category=categorize(current.app_name),
            title_length=len(current.window_title),
            app_changed=app_changed,
            is_first_time_app_today=current.app_name not in apps_seen_today,
            switches_last_5min=switches_last_5min,
        )