from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.app.logging import configure_logging
from src.app.health import router as health_router
from src.api.routes_webhook import router as webhook_router
from src.api.routes_admin import router as admin_router


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(title="Team Communication Analytics Bot")

    @app.middleware("http")
    async def error_handling_middleware(request: Request, call_next):  # type: ignore[override]
        try:
            response = await call_next(request)
            return response
        except Exception as exc:  # noqa: BLE001
            # simple JSON error wrapper with logging handled by root logger
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal Server Error"},
            )

    app.include_router(health_router)
    app.include_router(webhook_router)
    app.include_router(admin_router)

    return app

