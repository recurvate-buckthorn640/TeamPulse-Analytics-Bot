from typing import Any, Dict

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.services.ingestion_service import IngestionService


router = Router()


@router.message(Command(commands=["ping"]))
async def handle_ping(message: Message) -> None:
    await message.answer("pong")


@router.message()
async def handle_any_message(message: Message) -> None:
    # This path is primarily for local testing; production uses webhook via FastAPI.
    payload: Dict[str, Any] = message.model_dump()
    IngestionService.handle_update({"update_id": message.message_id, "message": payload})

from src.services.ingestion_service import IngestionService


def handle_update(payload: dict) -> None:
    IngestionService.handle_update(payload)

