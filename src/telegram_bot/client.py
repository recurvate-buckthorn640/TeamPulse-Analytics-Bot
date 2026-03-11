from aiogram import Bot, Dispatcher

from src.app.config import settings
from src.telegram_bot.handlers import router as handlers_router


def get_bot() -> Bot:
    return Bot(token=settings.telegram_bot_token)


def get_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(handlers_router)
    return dp


async def configure_webhook(webhook_url: str) -> None:
    """
    Wire aiogram bot webhook to FastAPI /webhook/telegram route.
    """
    bot = get_bot()
    await bot.set_webhook(
        url=webhook_url,
        secret_token=settings.telegram_webhook_secret,
    )

