from cogn_os.capture.types import WindowInfo
from cogn_os.config import Settings
from cogn_os.storage.factory import get_repositories


def test_get_repositories_creates_working_sqlite_backed_repos(tmp_path):
    db_file = tmp_path / "test_cognos.db"
    settings = Settings(_env_file=None, database_url=f"sqlite:///{db_file}")

    repos = get_repositories(settings)

    repos.events.add(WindowInfo.now("a.exe", "hello"))
    repos.suggestions.add(WindowInfo.now("a.exe", "hello"), "a suggestion")

    assert repos.events.count() == 1
    assert len(repos.suggestions.recent()) == 1
    assert db_file.exists()  # proves it actually wrote to disk, not just in-memory