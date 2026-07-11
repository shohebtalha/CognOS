from cogn_os.capture.types import WindowInfo
from cogn_os.storage.sqlalchemy_repository import SqlAlchemyEventRepository


def test_add_and_recent_returns_in_chronological_order(sqlite_session_factory):
    repo = SqlAlchemyEventRepository(sqlite_session_factory)

    w1 = WindowInfo.now("a.exe", "first")
    w2 = WindowInfo.now("b.exe", "second")
    w3 = WindowInfo.now("c.exe", "third")

    repo.add(w1)
    repo.add(w2)
    repo.add(w3)

    result = repo.recent(limit=10)

    assert [w.app_name for w in result] == ["a.exe", "b.exe", "c.exe"]


def test_recent_respects_limit(sqlite_session_factory):
    repo = SqlAlchemyEventRepository(sqlite_session_factory)
    for i in range(5):
        repo.add(WindowInfo.now(f"app{i}.exe", f"title{i}"))

    result = repo.recent(limit=2)

    assert len(result) == 2
    # limit=2 should return the *most recent* two, still chronological
    assert [w.app_name for w in result] == ["app3.exe", "app4.exe"]


def test_recent_on_empty_repository_returns_empty_list(sqlite_session_factory):
    repo = SqlAlchemyEventRepository(sqlite_session_factory)
    assert repo.recent() == []


def test_count_reflects_number_of_events(sqlite_session_factory):
    repo = SqlAlchemyEventRepository(sqlite_session_factory)
    assert repo.count() == 0

    repo.add(WindowInfo.now("a.exe", "t"))
    repo.add(WindowInfo.now("b.exe", "t"))

    assert repo.count() == 2