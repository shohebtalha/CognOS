from cogn_os.capture.fake_source import FakeWindowInfoSource
from cogn_os.capture.types import WindowInfo
from cogn_os.config import Settings
from cogn_os.service.clock import FakeClock
from cogn_os.service.wiring import build_storage_backed_loop
from cogn_os.storage.sqlalchemy_repository import SqlAlchemyEventRepository


def test_storage_backed_loop_persists_window_changes(sqlite_session_factory):
    event_repo = SqlAlchemyEventRepository(sqlite_session_factory)
    settings = Settings(_env_file=None, poll_interval_seconds=1.0)

    w1 = WindowInfo.now("code.exe", "main.py")
    w2 = WindowInfo.now("browser.exe", "docs")
    source = FakeWindowInfoSource([w1, w2])
    clock = FakeClock()

    loop = build_storage_backed_loop(settings, source, clock, event_repo)
    loop.run(max_ticks=2)

    stored = event_repo.recent(limit=10)
    assert [e.app_name for e in stored] == ["code.exe", "browser.exe"]


def test_storage_backed_loop_respects_excluded_apps(sqlite_session_factory):
    event_repo = SqlAlchemyEventRepository(sqlite_session_factory)
    settings = Settings(_env_file=None, excluded_apps_raw="LockApp.exe")

    w1 = WindowInfo.now("LockApp.exe", "Lock")
    source = FakeWindowInfoSource([w1])
    clock = FakeClock()

    loop = build_storage_backed_loop(settings, source, clock, event_repo)
    loop.run(max_ticks=1)

    assert event_repo.count() == 0