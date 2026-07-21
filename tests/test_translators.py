from datetime import timezone

from cogn_os.plugins.events import ContextEvent
from cogn_os.plugins.translators import window_info_from_event


def test_window_changed_event_translates_correctly():
    event = ContextEvent.now(
        source="window_tracker",
        event_type="window_changed",
        payload={"app_name": "code.exe", "window_title": "main.py"},
    )
    info = window_info_from_event(event)

    assert info is not None
    assert info.app_name == "code.exe"
    assert info.window_title == "main.py"
    assert info.captured_at == event.captured_at
    assert info.captured_at.tzinfo == timezone.utc


def test_non_window_event_returns_none():
    event = ContextEvent.now(source="clipboard", event_type="clipboard_changed")
    assert window_info_from_event(event) is None


def test_unknown_event_type_returns_none():
    event = ContextEvent.now(source="ocr", event_type="screen_text_detected")
    assert window_info_from_event(event) is None