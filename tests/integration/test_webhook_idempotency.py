from fastapi.testclient import TestClient
from sqlalchemy import select

from src.app.main import create_app
from src.api.deps import SessionLocal
from src.db.models import Message


app = create_app()
client = TestClient(app)


def test_duplicate_update_idempotency() -> None:
    payload = {
        "update_id": 10,
        "message": {
            "message_id": 99,
            "date": 1_700_000_010,
            "chat": {"id": -100555, "type": "supergroup", "title": "Team"},
            "from": {"id": 999, "is_bot": False, "first_name": "Idem"},
            "text": "idempotent",
        },
    }

    # Send the same update twice
    resp1 = client.post("/webhook/telegram", json=payload)
    resp2 = client.post("/webhook/telegram", json=payload)

    assert resp1.status_code == 200
    assert resp2.status_code == 200

    # Verify only one message row exists for the idempotency key
    idempotency_key = f"{payload['message']['chat']['id']}:{payload['message']['message_id']}:{payload['message']['date']}"

    session = SessionLocal()
    try:
        rows = session.execute(
            select(Message).where(Message.idempotency_key == idempotency_key)
        ).scalars().all()
        assert len(rows) == 1
    finally:
        session.close()

