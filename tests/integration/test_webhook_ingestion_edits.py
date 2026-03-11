from fastapi.testclient import TestClient

from src.app.main import create_app


app = create_app()
client = TestClient(app)


def test_edited_message_handling() -> None:
    base_payload = {
        "update_id": 3,
        "message": {
            "message_id": 12,
            "date": 1_700_000_002,
            "chat": {"id": -100123, "type": "supergroup", "title": "Team"},
            "from": {"id": 333, "is_bot": False, "first_name": "Carol"},
            "text": "original",
        },
    }
    edited_payload = {
        "update_id": 4,
        "edited_message": {
            "message_id": 12,
            "date": 1_700_000_003,
            "chat": {"id": -100123, "type": "supergroup", "title": "Team"},
            "from": {"id": 333, "is_bot": False, "first_name": "Carol"},
            "text": "edited",
        },
    }

    resp1 = client.post("/webhook/telegram", json=base_payload)
    resp2 = client.post("/webhook/telegram", json=edited_payload)

    assert resp1.status_code == 200
    assert resp2.status_code == 200

