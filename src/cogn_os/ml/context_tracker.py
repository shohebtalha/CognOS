"""
Owns the rolling state that FeatureExtractor needs but that a single
event alone doesn't carry: history of recent events, which apps have
been seen today, and when the LLM was last actually called. Kept as
its own class (not inline in the capture loop) so it's independently
testable and the loop itself stays as simple as it was on Day 3.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from cogn_os.capture.types import WindowInfo

DEFAULT_HISTORY_WINDOW = timedelta(minutes=10)


class ContextTracker:
    def __init__(self, history_window: timedelta = DEFAULT_HISTORY_WINDOW) -> None:
        self._history_window = history_window
        self._history: list[WindowInfo] = []
        self._apps_seen_today: set[str] = set()
        self._current_day: int | None = None
        self._last_llm_call_at: datetime | None = None
        self._previous: WindowInfo | None = None

    def record_event(self, info: WindowInfo) -> None:
        """Call once per observed event, before extracting features for it."""
        self._reset_daily_state_if_new_day(info.captured_at)
        self._apps_seen_today.add(info.app_name)
        self._trim_old_history(info.captured_at)
        self._history.append(info)

    def record_llm_call(self, at: datetime) -> None:
        self._last_llm_call_at = at

    def set_previous(self, info: WindowInfo | None) -> None:
        self._previous = info

    @property
    def previous(self) -> WindowInfo | None:
        return self._previous

    @property
    def history(self) -> list[WindowInfo]:
        return list(self._history)

    @property
    def apps_seen_today(self) -> set[str]:
        return set(self._apps_seen_today)

    @property
    def last_llm_call_at(self) -> datetime | None:
        return self._last_llm_call_at

    def _reset_daily_state_if_new_day(self, ts: datetime) -> None:
        day_ordinal = ts.toordinal()
        if self._current_day is not None and day_ordinal != self._current_day:
            self._apps_seen_today.clear()
        self._current_day = day_ordinal

    def _trim_old_history(self, now: datetime) -> None:
        cutoff = now - self._history_window
        self._history = [e for e in self._history if e.captured_at >= cutoff]