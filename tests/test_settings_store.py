from cogn_os.settings_store import SettingsStore


def test_settings_store_creates_defaults(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")

    settings = store.load()

    assert settings.ocr_monitor_enabled is True
    assert settings.llm_model == "llama3.2:latest"


def test_settings_store_updates_allowed_fields(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")

    settings = store.update({"clipboard_monitor_enabled": True, "unknown": "ignored"})

    assert settings.clipboard_monitor_enabled is True
    assert not hasattr(settings, "unknown")
