from cogn_os.capture.fake_source import FakeWindowInfoSource
from cogn_os.capture.types import WindowInfo
from cogn_os.config import Settings
from cogn_os.ml.fake_suggestion_gate import FakeSuggestionGate
from cogn_os.service.clock import FakeClock
from cogn_os.service.wiring import build_ml_gated_loop
from cogn_os.storage.sqlalchemy_repository import SqlAlchemyEventRepository


def test_every_change_logged_regardless_of_gate_decision(sqlite_session_factory):
    event_repo = SqlAlchemyEventRepository(sqlite_session_factory)
    settings = Settings(_env_file=None)
    gate = FakeSuggestionGate(sequence=False)  # never flags anything
    flagged_events = []

    w1 = WindowInfo.now("a.exe", "t1")
    w2 = WindowInfo.now("b.exe", "t2")
    loop = build_ml_gated_loop(
        settings, FakeWindowInfoSource([w1, w2]), FakeClock(), event_repo,
        gate, on_flagged=flagged_events.append,
    )
    loop.run(max_ticks=2)

    assert event_repo.count() == 2  # both logged
    assert flagged_events == []      # gate said no every time


def test_flagged_events_trigger_on_flagged_callback(sqlite_session_factory):
    event_repo = SqlAlchemyEventRepository(sqlite_session_factory)
    settings = Settings(_env_file=None)
    gate = FakeSuggestionGate(sequence=True)  # always flags
    flagged_events = []

    w1 = WindowInfo.now("code.exe", "main.py")
    loop = build_ml_gated_loop(
        settings, FakeWindowInfoSource([w1]), FakeClock(), event_repo,
        gate, on_flagged=flagged_events.append,
    )
    loop.run(max_ticks=1)

    assert len(flagged_events) == 1
    assert flagged_events[0].app_name == "code.exe"


def test_gate_receives_correctly_populated_features(sqlite_session_factory):
    event_repo = SqlAlchemyEventRepository(sqlite_session_factory)
    settings = Settings(_env_file=None)
    gate = FakeSuggestionGate(sequence=True)

    w1 = WindowInfo.now("code.exe", "main.py")
    loop = build_ml_gated_loop(
        settings, FakeWindowInfoSource([w1]), FakeClock(), event_repo,
        gate, on_flagged=lambda info: None,
    )
    loop.run(max_ticks=1)

    assert len(gate.received_features) == 1
    features = gate.received_features[0]
    assert features.is_first_time_app_today is True  # first-ever event
    assert features.app_changed is True


def test_gate_exception_does_not_crash_loop(sqlite_session_factory):
    class ExplodingGate:
        def should_flag(self, features):
            raise RuntimeError("model exploded")

    event_repo = SqlAlchemyEventRepository(sqlite_session_factory)
    settings = Settings(_env_file=None)
    flagged_events = []

    w1 = WindowInfo.now("code.exe", "main.py")
    loop = build_ml_gated_loop(
        settings, FakeWindowInfoSource([w1]), FakeClock(), event_repo,
        ExplodingGate(), on_flagged=flagged_events.append,
    )
    loop.run(max_ticks=1)  # should not raise

    assert event_repo.count() == 1  # event still logged despite gate failure
    assert flagged_events == []


def test_excluded_apps_never_reach_the_gate(sqlite_session_factory):
    event_repo = SqlAlchemyEventRepository(sqlite_session_factory)
    settings = Settings(_env_file=None, excluded_apps_raw="LockApp.exe")
    gate = FakeSuggestionGate(sequence=True)

    w1 = WindowInfo.now("LockApp.exe", "Lock")
    loop = build_ml_gated_loop(
        settings, FakeWindowInfoSource([w1]), FakeClock(), event_repo,
        gate, on_flagged=lambda info: None,
    )
    loop.run(max_ticks=1)

    assert gate.received_features == []  # never even called
    assert event_repo.count() == 0