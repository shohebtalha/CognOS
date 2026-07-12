from cogn_os.screenshot.types import Screenshot
from cogn_os.storage.sqlalchemy_repository import SqlAlchemyScreenshotRepository


def test_add_returns_assigned_id(sqlite_session_factory):
    repo = SqlAlchemyScreenshotRepository(sqlite_session_factory)
    shot = Screenshot.now(image_b64="abc", width=800, height=600)

    new_id = repo.add(shot)

    assert isinstance(new_id, int)
    assert repo.count() == 1


def test_add_links_to_event_id(sqlite_session_factory):
    repo = SqlAlchemyScreenshotRepository(sqlite_session_factory)
    shot = Screenshot.now(image_b64="abc", width=1, height=1)

    repo.add(shot, event_id=42)

    assert repo.count() == 1


def test_add_without_event_id_is_allowed(sqlite_session_factory):
    repo = SqlAlchemyScreenshotRepository(sqlite_session_factory)
    shot = Screenshot.now(image_b64="abc", width=1, height=1)

    repo.add(shot)  # event_id defaults to None

    assert repo.count() == 1