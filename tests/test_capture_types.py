from datetime import timezone

from cogn_os.capture.fake_source import FakeWindowInfoSource
from cogn_os.capture.types import WindowInfo


def test_window_info_now_sets_utc_timestamp():
    info = WindowInfo.now(app_name="code.exe", window_title="main.py")
    assert info.app_name == "code.exe"
    assert info.window_title == "main.py"
    assert info.captured_at.tzinfo == timezone.utc


def test_window_info_is_frozen():
    info = WindowInfo.now(app_name="a.exe", window_title="t")
    try:
        info.app_name = "b.exe"  # type: ignore[misc]
        assert False, "expected FrozenInstanceError"
    except AttributeError:
        pass


def test_fake_source_plays_back_sequence_in_order():
    w1 = WindowInfo.now("a.exe", "t1")
    w2 = WindowInfo.now("b.exe", "t2")
    source = FakeWindowInfoSource([w1, w2])

    assert source.get_active_window() is w1
    assert source.get_active_window() is w2
    assert source.call_count == 2


def test_fake_source_repeats_last_value_after_exhausted():
    w1 = WindowInfo.now("a.exe", "t1")
    source = FakeWindowInfoSource([w1])

    source.get_active_window()
    second_call = source.get_active_window()
    third_call = source.get_active_window()
    assert second_call is w1
    assert third_call is w1


def test_fake_source_handles_empty_sequence():
    source = FakeWindowInfoSource([])
    assert source.get_active_window() is None


def test_fake_source_can_include_none_gaps():
    w1 = WindowInfo.now("a.exe", "t1")
    source = FakeWindowInfoSource([w1, None, w1])
    assert source.get_active_window() is w1
    assert source.get_active_window() is None
    assert source.get_active_window() is w1