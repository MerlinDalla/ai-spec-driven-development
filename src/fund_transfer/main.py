from __future__ import annotations
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from fund_transfer.api.middleware.correlation import CorrelationMiddleware
from fund_transfer.api.middleware.error_handler import register_exception_handlers
from fund_transfer.core.config import get_settings
from fund_transfer.core.database import engine

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    # Load exchange rate config at startup to validate it
    settings.get_exchange_rate_config()
    logger.info("startup_complete", service=settings.SERVICE_NAME)
    yield
    # Dispose DB engine at shutdown
    await engine.dispose()
    logger.info("shutdown_complete", service=settings.SERVICE_NAME)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Fund Transfer Service",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Middleware (order matters - correlation first)
    app.add_middleware(CorrelationMiddleware)

    # Exception handlers
    register_exception_handlers(app)

    # Prometheus metrics
    Instrumentator().instrument(app).expose(app)

    # Routers (imported lazily to avoid circular imports)
    from fund_transfer.api.v1.router import api_router
    app.include_router(api_router)

    @app.get("/health", tags=["Health"])
    async def health_check() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    return app


app = create_app()
