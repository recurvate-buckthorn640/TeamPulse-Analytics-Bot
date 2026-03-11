from fastapi import APIRouter, Header, HTTPException, Request, Response, status

from src.services.ingestion_service import IngestionService
from src.app.config import settings


router = APIRouter()


@router.post("/webhook/telegram", status_code=status.HTTP_200_OK)
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> Response:
    expected_token = settings.telegram_webhook_secret
    if expected_token and x_telegram_bot_api_secret_token != expected_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid secret token")

    payload = await request.json()
    IngestionService.handle_update(payload)
    return Response(status_code=status.HTTP_200_OK)

