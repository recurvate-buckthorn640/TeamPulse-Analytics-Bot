from fastapi.testclient import TestClient

from src.app.main import create_app


app = create_app()
client = TestClient(app)


def test_new_message_ingested_successfully() -> None:
    payload = {
        "update_id": 2,
        "message": {
            "message_id": 11,
            "date": 1_700_000_001,
            "chat": {"id": -100123, "type": "supergroup", "title": "Team"},
            "from": {"id": 222, "is_bot": False, "first_name": "Bob"},
            "text": "hi",
        },
    }
    response = client.post("/webhook/telegram", json=payload)
    assert response.status_code == 200

