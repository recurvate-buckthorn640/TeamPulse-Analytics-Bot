from pydantic import BaseModel
from typing import Optional, List


class TelegramChat(BaseModel):
    id: int
    type: str
    title: Optional[str] = None


class TelegramUser(BaseModel):
    id: int
    is_bot: bool
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None


class MessageEntity(BaseModel):
    type: str
    offset: int
    length: int


class TelegramMessage(BaseModel):
    message_id: int
    date: int
    chat: TelegramChat
    from_: Optional[TelegramUser] = None
    reply_to_message: Optional["TelegramMessage"] = None
    text: Optional[str] = None
    entities: Optional[List[MessageEntity]] = None

    class Config:
        fields = {"from_": "from"}


class TelegramUpdate(BaseModel):
    update_id: int
    message: Optional[TelegramMessage] = None
    edited_message: Optional[TelegramMessage] = None


TelegramMessage.model_rebuild()

