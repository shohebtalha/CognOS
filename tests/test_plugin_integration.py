"""
Integration test: proves WindowObserver, registered into a real
PluginRegistry, produces the same ContextEvent stream a future
reasoning engine will consume — the first end-to-end proof that the
plugin architecture isn't just three isolated unit-tested classes.
"""

from __future__ import annotations

from cogn_os.capture.fake_source import FakeWindowInfoSource
from cogn_os.capture.types import WindowInfo
from cogn_os.plugins.registry import PluginRegistry
from cogn_os.plugins.window_observer import WindowObserver
from cogn_os.service.clock import FakeClock


def test_window_observer_through_registry_end_to_end():
    w1 = WindowInfo.now("code.exe", "main.py")
    w2 = WindowInfo.now("chrome.exe", "docs")
    source = FakeWindowInfoSource([w1, w2])
    observer = WindowObserver(source, poll_interval=1.0)

    clock = FakeClock(start=0.0)
    registry = PluginRegistry(clock)
    registry.register(observer)

    # First poll: interval hasn't elapsed relative to last_polled_at=0
    # and clock=0, so nothing fires without force.
    events = registry.poll_all(force=False)
    assert events == []

    clock.advance(2.0)
    events = registry.poll_all(force=False)
    assert len(events) == 1
    assert events[0].payload["app_name"] == "code.exe"

    clock.advance(2.0)
    events = registry.poll_all(force=False)
    assert len(events) == 1
    assert events[0].payload["app_name"] == "chrome.exe"


def test_multiple_plugins_including_window_observer_merge_into_one_stream():
    from cogn_os.plugins.events import ContextEvent
    from cogn_os.plugins.fake_observer import FakeObserver

    w1 = WindowInfo.now("code.exe", "main.py")
    window_observer = WindowObserver(FakeWindowInfoSource([w1]), poll_interval=1.0)
    clipboard_event = ContextEvent.now(source="clipboard", event_type="clipboard_changed")
    fake_clipboard_observer = FakeObserver("clipboard", [[clipboard_event]], poll_interval=1.0)

    registry = PluginRegistry(FakeClock())
    registry.register(window_observer)
    registry.register(fake_clipboard_observer)

    events = registry.poll_all(force=True)

    sources = {e.source for e in events}
    assert sources == {"window_tracker", "clipboard"}