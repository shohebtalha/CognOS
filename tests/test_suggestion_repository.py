from cogn_os.capture.types import WindowInfo
from cogn_os.storage.sqlalchemy_repository import SqlAlchemySuggestionRepository


def test_add_returns_dto_with_assigned_id(sqlite_session_factory):
    repo = SqlAlchemySuggestionRepository(sqlite_session_factory)
    info = WindowInfo.now("code.exe", "main.py — VS Code")

    dto = repo.add(info, "Your tests are failing on line 42.")

    assert dto.id is not None
    assert dto.app_name == "code.exe"
    assert dto.suggestion == "Your tests are failing on line 42."


def test_recent_returns_newest_first(sqlite_session_factory):
    repo = SqlAlchemySuggestionRepository(sqlite_session_factory)

    repo.add(WindowInfo.now("a.exe", "t1"), "first suggestion")
    repo.add(WindowInfo.now("b.exe", "t2"), "second suggestion")
    repo.add(WindowInfo.now("c.exe", "t3"), "third suggestion")

    result = repo.recent(limit=10)

    assert [s.suggestion for s in result] == [
        "third suggestion",
        "second suggestion",
        "first suggestion",
    ]


def test_recent_respects_limit(sqlite_session_factory):
    repo = SqlAlchemySuggestionRepository(sqlite_session_factory)
    for i in range(5):
        repo.add(WindowInfo.now(f"app{i}.exe", "t"), f"suggestion {i}")

    result = repo.recent(limit=2)

    assert len(result) == 2
    assert result[0].suggestion == "suggestion 4"


def test_recent_on_empty_repository_returns_empty_list(sqlite_session_factory):
    repo = SqlAlchemySuggestionRepository(sqlite_session_factory)
    assert repo.recent() == []