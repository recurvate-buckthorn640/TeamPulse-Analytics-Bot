from functools import lru_cache
from typing import Any, Dict

import httpx
from redis import Redis
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.app.config import settings


engine = create_engine(str(settings.database_url), future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def get_db_session() -> Session:
    return SessionLocal()


@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    return Redis.from_url(str(settings.redis_url))


@lru_cache(maxsize=1)
def get_http_client_for_llm() -> httpx.Client:
    timeout = httpx.Timeout(
        connect=settings.http_timeout_connect_seconds,
        read=settings.http_timeout_read_seconds,
        write=settings.http_timeout_write_seconds,
        pool=settings.http_timeout_pool_seconds,
    )
    limits = httpx.Limits(
        max_connections=settings.http_max_connections,
        max_keepalive_connections=settings.http_max_keepalive_connections,
    )
    return httpx.Client(timeout=timeout, limits=limits)


@lru_cache(maxsize=1)
def get_http_client_for_telegram() -> httpx.AsyncClient:
    timeout = httpx.Timeout(
        connect=settings.http_timeout_connect_seconds,
        read=settings.http_timeout_read_seconds,
        write=settings.http_timeout_write_seconds,
        pool=settings.http_timeout_pool_seconds,
    )
    limits = httpx.Limits(
        max_connections=settings.http_max_connections,
        max_keepalive_connections=settings.http_max_keepalive_connections,
    )
    return httpx.AsyncClient(timeout=timeout, limits=limits)

