from fastapi.testclient import TestClient

from src.app.main import create_app


app = create_app()
client = TestClient(app)


def test_telegram_webhook_accepts_valid_payload() -> None:
    payload = {
        "update_id": 1,
        "message": {
            "message_id": 10,
            "date": 1_700_000_000,
            "chat": {"id": -100123, "type": "supergroup", "title": "Team"},
            "from": {"id": 111, "is_bot": False, "first_name": "Alice"},
            "text": "hello",
        },
    }
    response = client.post("/webhook/telegram", json=payload)
    assert response.status_code == 200

