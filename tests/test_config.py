import pytest

from cogn_os.config import Settings, get_settings


def test_defaults_are_sane():
    s = Settings(_env_file=None)
    assert s.poll_interval_seconds == 3.0
    assert s.min_seconds_between_llm_calls == 60.0
    assert "LockApp.exe" in s.excluded_apps
    assert s.database_url.startswith("sqlite:///")


def test_env_prefix_overrides(monkeypatch):
    monkeypatch.setenv("COGNOS_POLL_INTERVAL_SECONDS", "5")
    monkeypatch.setenv("COGNOS_API_PORT", "9000")
    s = Settings(_env_file=None)
    assert s.poll_interval_seconds == 5.0
    assert s.api_port == 9000


def test_excluded_apps_parsed_from_csv_string(monkeypatch):
    monkeypatch.setenv("COGNOS_EXCLUDED_APPS_RAW", "bank.exe, passwords.exe ,LockApp.exe")
    s = Settings(_env_file=None)
    assert s.excluded_apps == frozenset({"bank.exe", "passwords.exe", "LockApp.exe"})


def test_excluded_apps_ignores_blank_entries(monkeypatch):
    monkeypatch.setenv("COGNOS_EXCLUDED_APPS_RAW", "a.exe,,  ,b.exe")
    s = Settings(_env_file=None)
    assert s.excluded_apps == frozenset({"a.exe", "b.exe"})


def test_poll_interval_must_be_positive():
    with pytest.raises(ValueError):
        Settings(_env_file=None, poll_interval_seconds=0)


def test_get_settings_factory_reads_env(monkeypatch):
    monkeypatch.setenv("COGNOS_API_HOST", "0.0.0.0")
    s = get_settings()
    assert s.api_host == "0.0.0.0"