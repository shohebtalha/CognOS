from cogn_os.capture.types import WindowInfo
from cogn_os.config import Settings
from cogn_os.ml.fake_suggestion_gate import FakeSuggestionGate
from cogn_os.plugins.events import ContextEvent
from cogn_os.plugins.fake_observer import FakeObserver
from cogn_os.plugins.orchestrator import PluginOrchestrator
from cogn_os.plugins.registry import PluginRegistry
from cogn_os.service.clock import FakeClock
from cogn_os.storage.sqlalchemy_repository import SqlAlchemyEventRepository


def window_event(app: str, title: str) -> ContextEvent:
    return ContextEvent.now(source="window_tracker", event_type="window_changed",
                             payload={"app_name": app, "window_title": title})


def test_window_events_are_logged_regardless_of_gate_decision(sqlite_session_factory):
    event_repo = SqlAlchemyEventRepository(sqlite_session_factory)
    settings = Settings(_env_file=None, min_seconds_between_llm_calls=0.001)
    gate = FakeSuggestionGate(sequence=False)
    flagged = []

    registry = PluginRegistry(FakeClock())
    registry.register(FakeObserver("window_tracker", [[window_event("code.exe", "t1")],
                                                        [window_event("chrome.exe", "t2")]],
                                    poll_interval=0.0))

    orchestrator = PluginOrchestrator(
        registry, FakeClock(), settings, event_repo, gate,
        on_flagged=lambda info, history, ocr_text: flagged.append(info),
    )
    orchestrator.run(max_ticks=2)

    assert event_repo.count() == 2
    assert flagged == []


def test_flagged_window_event_triggers_on_flagged(sqlite_session_factory):
    event_repo = SqlAlchemyEventRepository(sqlite_session_factory)
    settings = Settings(_env_file=None, min_seconds_between_llm_calls=0.001)
    gate = FakeSuggestionGate(sequence=True)
    flagged = []

    registry = PluginRegistry(FakeClock())
    registry.register(FakeObserver("window_tracker", [[window_event("code.exe", "main.py")]],
                                    poll_interval=0.0))

    orchestrator = PluginOrchestrator(
        registry, FakeClock(), settings, event_repo, gate,
        on_flagged=lambda info, history, ocr_text: flagged.append(info),
    )
    orchestrator.run(max_ticks=1)

    assert len(flagged) == 1
    assert flagged[0].app_name == "code.exe"


def test_sensitive_window_event_never_stored_or_flagged(sqlite_session_factory):
    event_repo = SqlAlchemyEventRepository(sqlite_session_factory)
    settings = Settings(_env_file=None, min_seconds_between_llm_calls=0.001)
    gate = FakeSuggestionGate(sequence=True)
    flagged = []

    registry = PluginRegistry(FakeClock())
    registry.register(FakeObserver(
        "window_tracker",
        [[window_event("chrome.exe", "Bank of Example - Sign In")]],
        poll_interval=0.0,
    ))

    orchestrator = PluginOrchestrator(
        registry, FakeClock(), settings, event_repo, gate,
        on_flagged=lambda info, history,ocr_text: flagged.append(info),
    )
    orchestrator.run(max_ticks=1)

    assert event_repo.count() == 0
    assert flagged == []


def test_non_window_events_are_skipped_without_error(sqlite_session_factory):
    event_repo = SqlAlchemyEventRepository(sqlite_session_factory)
    settings = Settings(_env_file=None, min_seconds_between_llm_calls=0.001)
    gate = FakeSuggestionGate(sequence=True)

    clipboard_event = ContextEvent.now(source="clipboard", event_type="clipboard_changed")
    registry = PluginRegistry(FakeClock())
    registry.register(FakeObserver("clipboard", [[clipboard_event]], poll_interval=0.0))

    orchestrator = PluginOrchestrator(
        registry, FakeClock(), settings, event_repo, gate,
        on_flagged=lambda info, history: None,
    )
    processed = orchestrator.run_once()  # must not raise

    assert processed == []  # no processing path for clipboard yet — documented, expected
    assert event_repo.count() == 0


def test_multiple_plugins_only_window_events_get_processed(sqlite_session_factory):
    event_repo = SqlAlchemyEventRepository(sqlite_session_factory)
    settings = Settings(_env_file=None, min_seconds_between_llm_calls=0.001)
    gate = FakeSuggestionGate(sequence=False)

    registry = PluginRegistry(FakeClock())
    registry.register(FakeObserver("window_tracker", [[window_event("code.exe", "main.py")]],
                                    poll_interval=0.0))
    registry.register(FakeObserver(
        "clipboard", [[ContextEvent.now(source="clipboard", event_type="clipboard_changed")]],
        poll_interval=0.0,
    ))

    orchestrator = PluginOrchestrator(
        registry, FakeClock(), settings, event_repo, gate,
        on_flagged=lambda info, history: None,
    )
    orchestrator.run_once()

    assert event_repo.count() == 1  # only the window event got processed/stored