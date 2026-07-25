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
