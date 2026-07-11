from cogn_os.capture.fake_source import FakeWindowInfoSource
from cogn_os.capture.types import WindowInfo
from cogn_os.service.capture_loop import CaptureLoop
from cogn_os.service.clock import FakeClock


def make_loop(sequence, excluded_apps=frozenset(), poll_interval=1.0):
    source = FakeWindowInfoSource(sequence)
    clock = FakeClock()
    seen: list[WindowInfo] = []
    loop = CaptureLoop(
        source=source,
        clock=clock,
        poll_interval_seconds=poll_interval,
        excluded_apps=excluded_apps,
        on_window_changed=seen.append,
    )
    return loop, seen, clock


def test_callback_fires_on_first_window_seen():
    w1 = WindowInfo.now("a.exe", "t1")
    loop, seen, _ = make_loop([w1])
    loop.run_once()
    assert seen == [w1]


def test_callback_does_not_fire_on_unchanged_window():
    w1 = WindowInfo.now("a.exe", "t1")
    loop, seen, _ = make_loop([w1, w1, w1])
    loop.run_once()
    loop.run_once()
    loop.run_once()
    assert seen == [w1]  # only the first call, not repeated


def test_callback_fires_again_when_window_changes():
    w1 = WindowInfo.now("a.exe", "t1")
    w2 = WindowInfo.now("b.exe", "t2")
    loop, seen, _ = make_loop([w1, w2])
    loop.run_once()
    loop.run_once()
    assert [w.app_name for w in seen] == ["a.exe", "b.exe"]


def test_excluded_app_does_not_trigger_callback():
    w1 = WindowInfo.now("LockApp.exe", "Lock Screen")
    loop, seen, _ = make_loop([w1], excluded_apps=frozenset({"LockApp.exe"}))
    loop.run_once()
    assert seen == []


def test_none_from_source_is_skipped_without_error():
    loop, seen, _ = make_loop([None])
    loop.run_once()
    assert seen == []


def test_run_with_max_ticks_calls_sleep_between_ticks():
    # sleep() only happens *between* ticks, not after the final one —
    # with max_ticks=3 there are 3 run_once() calls but only 2 sleeps.
    w1 = WindowInfo.now("a.exe", "t1")
    loop, seen, clock = make_loop([w1, w1, w1], poll_interval=2.0)
    loop.run(max_ticks=3)
    assert clock.sleep_calls == [2.0, 2.0]
    assert loop.tick_count == 3

    
def test_stop_halts_the_loop():
    # Each window differs from the last so on_window_changed fires every
    # tick — otherwise stop() (called from inside that callback) never
    # gets invoked again after the first tick, and the loop never ends.
    windows = [WindowInfo.now(f"app{i}.exe", f"t{i}") for i in range(100)]
    source = FakeWindowInfoSource(windows)
    clock = FakeClock()
    loop = CaptureLoop(
        source=source, clock=clock, poll_interval_seconds=1.0,
        excluded_apps=frozenset(),
        on_window_changed=lambda info: loop.stop() if loop.tick_count >= 3 else None,
    )
    loop.run()
    assert loop.tick_count == 3