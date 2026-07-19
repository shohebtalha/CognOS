from datetime import timezone

from cogn_os.plugins.events import ContextEvent


def test_now_sets_utc_timestamp_and_defaults():
    event = ContextEvent.now(source="ocr", event_type="screen_text_detected")
    assert event.source == "ocr"
    assert event.event_type == "screen_text_detected"
    assert event.payload == {}
    assert event.confidence is None
    assert event.captured_at.tzinfo == timezone.utc


def test_now_accepts_payload_and_confidence():
    event = ContextEvent.now(
        source="ocr",
        event_type="screen_text_detected",
        payload={"text": "ModuleNotFoundError"},
        confidence=0.87,
    )
    assert event.payload == {"text": "ModuleNotFoundError"}
    assert event.confidence == 0.87


def test_is_frozen():
    event = ContextEvent.now(source="clipboard", event_type="clipboard_changed")
    try:
        event.source = "other"  # type: ignore[misc]
        assert False, "expected FrozenInstanceError"
    except AttributeError:
        pass


def test_two_events_have_independent_payload_dicts():
    # default_factory=dict must not share a mutable default across instances
    e1 = ContextEvent.now(source="a", event_type="x")
    e2 = ContextEvent.now(source="b", event_type="y")
    e1.payload["key"] = "value"
    assert e2.payload == {}