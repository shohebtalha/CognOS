from cogn_os.capture.fake_source import FakeWindowInfoSource
from cogn_os.capture.types import WindowInfo
from cogn_os.plugins.window_observer import WindowObserver


def test_first_window_seen_produces_one_event():
    w1 = WindowInfo.now("code.exe", "main.py")
    observer = WindowObserver(FakeWindowInfoSource([w1]))

    events = observer.poll()

    assert len(events) == 1
    assert events[0].source == "window_tracker"
    assert events[0].event_type == "window_changed"
    assert events[0].payload == {"app_name": "code.exe", "window_title": "main.py"}


def test_unchanged_window_produces_no_event():
    w1 = WindowInfo.now("code.exe", "main.py")
    observer = WindowObserver(FakeWindowInfoSource([w1, w1, w1]))

    observer.poll()
    events_second = observer.poll()
    events_third = observer.poll()

    assert events_second == []
    assert events_third == []


def test_changed_window_produces_new_event():
    w1 = WindowInfo.now("code.exe", "main.py")
    w2 = WindowInfo.now("chrome.exe", "docs")
    observer = WindowObserver(FakeWindowInfoSource([w1, w2]))

    observer.poll()
    events = observer.poll()

    assert len(events) == 1
    assert events[0].payload["app_name"] == "chrome.exe"


def test_none_from_source_produces_no_event_and_does_not_crash():
    observer = WindowObserver(FakeWindowInfoSource([None]))
    events = observer.poll()
    assert events == []


def test_source_exception_produces_no_event_and_does_not_crash():
    class RaisingSource:
        def get_active_window(self):
            raise RuntimeError("OS call failed")

    observer = WindowObserver(RaisingSource())
    events = observer.poll()  # must not raise
    assert events == []


def test_name_property():
    observer = WindowObserver(FakeWindowInfoSource([]))
    assert observer.name == "window_tracker"


def test_custom_poll_interval():
    observer = WindowObserver(FakeWindowInfoSource([]), poll_interval=1.0)
    assert observer.poll_interval_seconds == 1.0