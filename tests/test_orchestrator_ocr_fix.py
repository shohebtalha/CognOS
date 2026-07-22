"""
Additional tests for PluginOrchestrator's on-demand OCR fix. Append
these to the existing tests/test_orchestrator.py rather than replacing
the file — the existing 5 tests (event logging, flagging, sensitive
content, non-window events, multi-plugin merging) are unaffected by
this change since screenshotter/ocr_engine default to None.
"""

from cogn_os.ocr.fake_engine import FakeOcrEngine
from cogn_os.ocr.engine import OcrResult
from cogn_os.screenshot.fake_screenshotter import FakeScreenshotter
from cogn_os.screenshot.types import Screenshot


def test_flagged_event_triggers_on_demand_ocr_and_passes_text_to_on_flagged(sqlite_session_factory):
    from cogn_os.capture.types import WindowInfo
    from cogn_os.config import Settings
    from cogn_os.ml.fake_suggestion_gate import FakeSuggestionGate
    from cogn_os.plugins.events import ContextEvent
    from cogn_os.plugins.fake_observer import FakeObserver
    from cogn_os.plugins.orchestrator import PluginOrchestrator
    from cogn_os.plugins.registry import PluginRegistry
    from cogn_os.service.clock import FakeClock
    from cogn_os.storage.sqlalchemy_repository import SqlAlchemyEventRepository

    event_repo = SqlAlchemyEventRepository(sqlite_session_factory)
    settings = Settings(_env_file=None, min_seconds_between_llm_calls=0.001)
    gate = FakeSuggestionGate(sequence=True)

    screenshot = Screenshot.now(image_b64="ZmFrZQ==", width=100, height=100)
    screenshotter = FakeScreenshotter(screenshot=screenshot)
    ocr_engine = FakeOcrEngine(text="ModuleNotFoundError: No module named requests", mean_confidence=90.0)

    received_ocr_text = []

    def on_flagged(info, history, ocr_text):
        received_ocr_text.append(ocr_text)

    window_event = ContextEvent.now(source="window_tracker", event_type="window_changed",
                                     payload={"app_name": "chrome.exe", "window_title": "error page"})
    registry = PluginRegistry(FakeClock())
    registry.register(FakeObserver("window_tracker", [[window_event]], poll_interval=0.0))

    orchestrator = PluginOrchestrator(
        registry, FakeClock(), settings, event_repo, gate, on_flagged,
        screenshotter=screenshotter, ocr_engine=ocr_engine,
    )
    orchestrator.run_once()

    assert received_ocr_text == ["ModuleNotFoundError: No module named requests"]
    assert screenshotter.call_count == 1  # captured exactly once, at flag time


def test_ocr_not_captured_when_event_is_not_flagged(sqlite_session_factory):
    from cogn_os.config import Settings
    from cogn_os.ml.fake_suggestion_gate import FakeSuggestionGate
    from cogn_os.plugins.events import ContextEvent
    from cogn_os.plugins.fake_observer import FakeObserver
    from cogn_os.plugins.orchestrator import PluginOrchestrator
    from cogn_os.plugins.registry import PluginRegistry
    from cogn_os.service.clock import FakeClock
    from cogn_os.storage.sqlalchemy_repository import SqlAlchemyEventRepository

    event_repo = SqlAlchemyEventRepository(sqlite_session_factory)
    settings = Settings(_env_file=None, min_seconds_between_llm_calls=0.001)
    gate = FakeSuggestionGate(sequence=False)  # never flags

    screenshot = Screenshot.now(image_b64="ZmFrZQ==", width=100, height=100)
    screenshotter = FakeScreenshotter(screenshot=screenshot)
    ocr_engine = FakeOcrEngine(text="some text", mean_confidence=90.0)

    window_event = ContextEvent.now(source="window_tracker", event_type="window_changed",
                                     payload={"app_name": "code.exe", "window_title": "main.py"})
    registry = PluginRegistry(FakeClock())
    registry.register(FakeObserver("window_tracker", [[window_event]], poll_interval=0.0))

    orchestrator = PluginOrchestrator(
        registry, FakeClock(), settings, event_repo, gate,
        on_flagged=lambda info, history, ocr_text: None,
        screenshotter=screenshotter, ocr_engine=ocr_engine,
    )
    orchestrator.run_once()

    assert screenshotter.call_count == 0  # never captured — not flagged, no OCR cost incurred


def test_low_confidence_ocr_result_is_treated_as_no_text(sqlite_session_factory):
    from cogn_os.config import Settings
    from cogn_os.ml.fake_suggestion_gate import FakeSuggestionGate
    from cogn_os.plugins.events import ContextEvent
    from cogn_os.plugins.fake_observer import FakeObserver
    from cogn_os.plugins.orchestrator import PluginOrchestrator
    from cogn_os.plugins.registry import PluginRegistry
    from cogn_os.service.clock import FakeClock
    from cogn_os.storage.sqlalchemy_repository import SqlAlchemyEventRepository

    event_repo = SqlAlchemyEventRepository(sqlite_session_factory)
    settings = Settings(_env_file=None, min_seconds_between_llm_calls=0.001)
    gate = FakeSuggestionGate(sequence=True)

    screenshot = Screenshot.now(image_b64="ZmFrZQ==", width=100, height=100)
    screenshotter = FakeScreenshotter(screenshot=screenshot)
    ocr_engine = FakeOcrEngine(text="garbled low confidence text", mean_confidence=10.0)

    received_ocr_text = []
    window_event = ContextEvent.now(source="window_tracker", event_type="window_changed",
                                     payload={"app_name": "chrome.exe", "window_title": "page"})
    registry = PluginRegistry(FakeClock())
    registry.register(FakeObserver("window_tracker", [[window_event]], poll_interval=0.0))

    orchestrator = PluginOrchestrator(
        registry, FakeClock(), settings, event_repo, gate,
        on_flagged=lambda info, history, ocr_text: received_ocr_text.append(ocr_text),
        screenshotter=screenshotter, ocr_engine=ocr_engine, on_demand_ocr_min_confidence=50.0,
    )
    orchestrator.run_once()

    assert received_ocr_text == [None]  # below confidence threshold, treated as unavailable


def test_no_screenshotter_configured_passes_none_ocr_text_without_error(sqlite_session_factory):
    from cogn_os.config import Settings
    from cogn_os.ml.fake_suggestion_gate import FakeSuggestionGate
    from cogn_os.plugins.events import ContextEvent
    from cogn_os.plugins.fake_observer import FakeObserver
    from cogn_os.plugins.orchestrator import PluginOrchestrator
    from cogn_os.plugins.registry import PluginRegistry
    from cogn_os.service.clock import FakeClock
    from cogn_os.storage.sqlalchemy_repository import SqlAlchemyEventRepository

    event_repo = SqlAlchemyEventRepository(sqlite_session_factory)
    settings = Settings(_env_file=None, min_seconds_between_llm_calls=0.001)
    gate = FakeSuggestionGate(sequence=True)

    received_ocr_text = []
    window_event = ContextEvent.now(source="window_tracker", event_type="window_changed",
                                     payload={"app_name": "chrome.exe", "window_title": "page"})
    registry = PluginRegistry(FakeClock())
    registry.register(FakeObserver("window_tracker", [[window_event]], poll_interval=0.0))

    orchestrator = PluginOrchestrator(
        registry, FakeClock(), settings, event_repo, gate,
        on_flagged=lambda info, history, ocr_text: received_ocr_text.append(ocr_text),
        # screenshotter/ocr_engine both omitted (None) — should not error
    )
    orchestrator.run_once()

    assert received_ocr_text == [None]