from typing import List, Optional

from pydantic_settings import BaseSettings
from pydantic import AnyUrl


class Settings(BaseSettings):
    database_url: AnyUrl
    redis_url: AnyUrl
    telegram_bot_token: str
    telegram_webhook_secret: Optional[str] = None
    llm_api_key: Optional[str] = None
    owner_telegram_user_ids: List[int] = []

    open_loop_threshold_hours: int = 24
    slow_response_threshold_hours: int = 4
    retention_days: int = 180

    http_timeout_connect_seconds: float = 3.0
    http_timeout_read_seconds: float = 15.0
    http_timeout_write_seconds: float = 15.0
    http_timeout_pool_seconds: float = 5.0
    http_max_connections: int = 100
    http_max_keepalive_connections: int = 20

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()

