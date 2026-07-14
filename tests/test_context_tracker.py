from datetime import datetime, timedelta, timezone

from cogn_os.capture.types import WindowInfo
from cogn_os.ml.context_tracker import ContextTracker


def w(app: str, title: str, ts: datetime) -> WindowInfo:
    return WindowInfo(app_name=app, window_title=title, captured_at=ts)


def test_record_event_adds_to_history():
    tracker = ContextTracker()
    base = datetime(2026, 7, 13, 10, 0, tzinfo=timezone.utc)
    tracker.record_event(w("code.exe", "t", base))
    assert len(tracker.history) == 1


def test_record_event_tracks_apps_seen_today():
    tracker = ContextTracker()
    base = datetime(2026, 7, 13, 10, 0, tzinfo=timezone.utc)
    tracker.record_event(w("code.exe", "t", base))
    tracker.record_event(w("chrome.exe", "t", base))
    assert tracker.apps_seen_today == {"code.exe", "chrome.exe"}


def test_apps_seen_today_resets_on_new_day():
    tracker = ContextTracker()
    day1 = datetime(2026, 7, 13, 23, 0, tzinfo=timezone.utc)
    day2 = datetime(2026, 7, 14, 1, 0, tzinfo=timezone.utc)

    tracker.record_event(w("code.exe", "t", day1))
    assert "code.exe" in tracker.apps_seen_today

    tracker.record_event(w("chrome.exe", "t", day2))
    assert tracker.apps_seen_today == {"chrome.exe"}  # code.exe cleared


def test_history_trims_events_older_than_window():
    tracker = ContextTracker(history_window=timedelta(minutes=5))
    base = datetime(2026, 7, 13, 10, 0, tzinfo=timezone.utc)

    tracker.record_event(w("a.exe", "t", base))
    tracker.record_event(w("b.exe", "t", base + timedelta(minutes=10)))

    # second record_event's "now" is 10 min after the first — first
    # event (10 min old at that point) is outside the 5-min window.
    assert [e.app_name for e in tracker.history] == ["b.exe"]


def test_record_llm_call_sets_last_call_time():
    tracker = ContextTracker()
    ts = datetime(2026, 7, 13, 10, 0, tzinfo=timezone.utc)
    assert tracker.last_llm_call_at is None
    tracker.record_llm_call(ts)
    assert tracker.last_llm_call_at == ts


def test_set_and_get_previous():
    tracker = ContextTracker()
    ts = datetime(2026, 7, 13, 10, 0, tzinfo=timezone.utc)
    info = w("a.exe", "t", ts)
    tracker.set_previous(info)
    assert tracker.previous is info


def test_previous_defaults_to_none():
    tracker = ContextTracker()
    assert tracker.previous is None