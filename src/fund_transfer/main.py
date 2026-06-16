from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import select

from fund_transfer.api.middleware.correlation import CorrelationMiddleware
from fund_transfer.api.middleware.error_handler import register_exception_handlers
from fund_transfer.core.config import get_settings
from fund_transfer.core.database import engine, get_session
from fund_transfer.services.fx_rate_provider import FxRateProvider, StaticFxRateProvider, TreasuryFeedAdapter

logger = structlog.get_logger()


async def _bg_refresh_loop(provider: TreasuryFeedAdapter, interval: int) -> None:
    while True:
        await asyncio.sleep(interval)
        try:
            await provider.refresh()
        except Exception:
            pass


async def get_fx_provider(request: Request) -> FxRateProvider:
    return request.app.state.fx_provider


async def _seed_currency_pairs(session) -> None:
    from fund_transfer.models.currency_pair import CurrencyPair

    result = await session.execute(select(CurrencyPair).limit(1))
    if result.scalar_one_or_none() is not None:
        return
    pairs = [
        ("EUR", "USD"),
        ("USD", "EUR"),
        ("EUR", "GBP"),
        ("GBP", "EUR"),
        ("USD", "GBP"),
        ("GBP", "USD"),
        ("EUR", "CHF"),
        ("CHF", "EUR"),
    ]
    async with session.begin():
        for from_c, to_c in pairs:
            session.add(CurrencyPair(id=uuid.uuid4(), from_currency=from_c, to_currency=to_c))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    settings.get_exchange_rate_config()

    if settings.USE_STATIC_RATES:
        provider = StaticFxRateProvider(settings.get_exchange_rate_config())
    else:
        provider = TreasuryFeedAdapter(settings.FX_PROVIDER_URL, settings.FX_PROVIDER_TIMEOUT_SECONDS)
        try:
            await provider.refresh()
        except Exception:
            pass
    app.state.fx_provider = provider

    task = None
    if not settings.USE_STATIC_RATES:
        task = asyncio.create_task(_bg_refresh_loop(provider, settings.FX_REFRESH_INTERVAL_SECONDS))

    try:
        async for session in get_session():
            await _seed_currency_pairs(session)
            break
    except Exception:
        pass

    logger.info("startup_complete", service=settings.SERVICE_NAME)
    yield

    if task is not None:
        task.cancel()
    await engine.dispose()
    logger.info("shutdown_complete", service=settings.SERVICE_NAME)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Fund Transfer Service",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(CorrelationMiddleware)
    register_exception_handlers(app)

    from fund_transfer.api.v1.router import api_router

    app.include_router(api_router)

    @app.get("/health", tags=["Health"])
    async def health_check() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    Instrumentator().instrument(app).expose(app)

    return app


app = create_app()
