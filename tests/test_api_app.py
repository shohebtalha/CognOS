from fastapi.testclient import TestClient

from cogn_os.api.app import create_app
from cogn_os.config import Settings


def test_health_endpoint(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'cognos.db'}")
    client = TestClient(create_app(settings))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_permissions_endpoint(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'cognos.db'}")
    client = TestClient(create_app(settings))

    response = client.get("/permissions")

    assert response.status_code == 200
    assert any(item["key"] == "active_window" for item in response.json())


def test_ingest_event_creates_assistant_card(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'cognos.db'}")
    client = TestClient(create_app(settings))

    response = client.post("/events/ingest", json={
        "source": "ocr",
        "event_type": "screen_text_detected",
        "payload": {"text": "Traceback (most recent call last):\nValueError: broken"},
        "confidence": 0.92,
    })

    assert response.status_code == 200
    cards = response.json()
    assert cards[0]["kind"] == "debugging"
    assert cards[0]["severity"] == "critical"


def test_cards_endpoint_returns_cards(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'cognos.db'}")
    client = TestClient(create_app(settings))
    client.post("/events/ingest", json={
        "source": "clipboard",
        "event_type": "clipboard_changed",
        "payload": {"text": "api_key = 'abcdefghijklmnopqrstuvwxyz'"},
    })

    response = client.get("/cards")

    assert response.status_code == 200
    assert response.json()[0]["kind"] == "security"


def test_settings_endpoint_updates_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'cognos.db'}")
    client = TestClient(create_app(settings))

    response = client.patch("/settings", json={"clipboard_monitor_enabled": True})

    assert response.status_code == 200
    assert response.json()["clipboard_monitor_enabled"] is True


def test_timeline_endpoint_records_ingested_events(tmp_path, monkeypatch):
    monkeypatch.setenv("COGNOS_SETTINGS_PATH", str(tmp_path / "settings.json"))
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'cognos.db'}")
    client = TestClient(create_app(settings))

    client.post("/events/ingest", json={
        "source": "browser_extension",
        "event_type": "browser_navigation",
        "payload": {"url": "https://example.com", "title": "Example"},
    })
    response = client.get("/timeline")

    assert response.status_code == 200
    assert response.json()[0]["source"] == "browser_extension"


def test_execute_action_requires_confirmation_for_file_index(tmp_path, monkeypatch):
    monkeypatch.setenv("COGNOS_SETTINGS_PATH", str(tmp_path / "settings.json"))
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'cognos.db'}")
    client = TestClient(create_app(settings))

    response = client.post("/actions/execute", json={
        "kind": "index_file",
        "payload": {"path": str(tmp_path / "sample.py")},
    })

    assert response.status_code == 200
    assert response.json()["requires_confirmation"] is True


def test_deep_health_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("COGNOS_SETTINGS_PATH", str(tmp_path / "settings.json"))
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'cognos.db'}")
    client = TestClient(create_app(settings))

    response = client.get("/health/deep")

    assert response.status_code == 200
    assert response.json()["checks"]["database"] is True
