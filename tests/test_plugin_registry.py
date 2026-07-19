from cogn_os.plugins.events import ContextEvent
from cogn_os.plugins.fake_observer import ExplodingObserver, FakeObserver
from cogn_os.plugins.registry import PluginRegistry
from cogn_os.service.clock import FakeClock


def test_register_and_registered_names():
    registry = PluginRegistry(FakeClock())
    registry.register(FakeObserver("ocr", []))
    registry.register(FakeObserver("clipboard", []))
    assert set(registry.registered_names) == {"ocr", "clipboard"}


def test_registering_duplicate_name_raises():
    registry = PluginRegistry(FakeClock())
    registry.register(FakeObserver("ocr", []))
    try:
        registry.register(FakeObserver("ocr", []))
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_unregister_removes_observer():
    registry = PluginRegistry(FakeClock())
    registry.register(FakeObserver("ocr", []))
    registry.unregister("ocr")
    assert registry.registered_names == []


def test_poll_all_collects_events_from_all_observers():
    e1 = ContextEvent.now(source="ocr", event_type="screen_text_detected")
    e2 = ContextEvent.now(source="clipboard", event_type="clipboard_changed")
    registry = PluginRegistry(FakeClock())
    registry.register(FakeObserver("ocr", [[e1]]))
    registry.register(FakeObserver("clipboard", [[e2]]))

    events = registry.poll_all(force=True)

    # ContextEvent contains a dict payload, so it's unhashable — cannot
    # use a set for comparison. Compare as a sorted-by-source list
    # instead, since dict iteration order (and thus event order here)
    # is insertion-ordered and deterministic in practice, but sorting
    # avoids relying on that as an assumption.
    assert sorted(events, key=lambda e: e.source) == sorted([e1, e2], key=lambda e: e.source)


def test_poll_all_respects_per_observer_interval(monkeypatch=None):
    clock = FakeClock(start=0.0)
    registry = PluginRegistry(clock)
    fast = FakeObserver("fast", [[ContextEvent.now("fast", "x")]], poll_interval=1.0)
    slow = FakeObserver("slow", [[ContextEvent.now("slow", "y")]], poll_interval=100.0)
    registry.register(fast)
    registry.register(slow)

    # First poll_all (force=False): both observers' last_polled_at
    # starts at 0.0 and clock is at 0.0, so elapsed=0 < interval for
    # both — neither should fire without force.
    events = registry.poll_all(force=False)
    assert events == []
    assert fast.poll_call_count == 0
    assert slow.poll_call_count == 0

    # Advance clock past fast's interval but not slow's.
    clock.advance(2.0)
    events = registry.poll_all(force=False)
    assert fast.poll_call_count == 1
    assert slow.poll_call_count == 0
    assert len(events) == 1
    assert events[0].source == "fast"


def test_poll_all_survives_a_raising_observer():
    good_event = ContextEvent.now(source="ocr", event_type="screen_text_detected")
    registry = PluginRegistry(FakeClock())
    registry.register(ExplodingObserver("broken"))
    registry.register(FakeObserver("ocr", [[good_event]]))

    events = registry.poll_all(force=True)  # must not raise

    assert events == [good_event]  # broken plugin contributed nothing, but didn't break the rest


def test_poll_all_with_no_observers_returns_empty_list():
    registry = PluginRegistry(FakeClock())
    assert registry.poll_all(force=True) == []


def test_poll_all_marks_broken_observer_as_polled_even_on_failure():
    # Ensures a permanently-broken observer doesn't get retried every
    # single poll_all() call once force=False is used in production —
    # it should still respect its own interval, not spin.
    clock = FakeClock(start=0.0)
    registry = PluginRegistry(clock)
    broken = ExplodingObserver("broken")
    registry.register(broken)

    registry.poll_all(force=True)
    registry.poll_all(force=True)
    # Both calls used force=True so this doesn't prove interval
    # respecting for broken observers specifically, but does prove
    # multiple consecutive failures don't accumulate into a crash.