from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.app.deps import get_db_session
from src.db.models import Chat, Message


router = APIRouter()


@router.get("/admin/chats")
def list_chats(db: Session = Depends(get_db_session)):
    stmt = (
        select(Chat.id, Chat.title, Chat.telegram_chat_id, func.count(Message.id).label("message_count"))
        .join(Message, Message.chat_id == Chat.id, isouter=True)
        .group_by(Chat.id)
    )
    rows = db.execute(stmt).all()
    return {
        "chats": [
            {
                "id": row.id,
                "title": row.title,
                "telegram_chat_id": row.telegram_chat_id,
                "message_count": row.message_count,
            }
            for row in rows
        ]
    }

