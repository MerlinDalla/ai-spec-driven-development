from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from prometheus_client import Gauge
from sqlalchemy.ext.asyncio import AsyncSession

from fund_transfer.api.middleware.auth import get_auth_principal
from fund_transfer.core.database import get_session
from fund_transfer.schemas.fx import ConversionPreviewRequest, ConversionPreviewResponse, RateTableResponse
from fund_transfer.services.fx_rate_service import FxRateService

router = APIRouter(prefix="/fx", tags=["FX Rates"])
FX_RATE_AGE_SECONDS = Gauge("fx_rate_age_seconds", "Age of latest FX snapshot in seconds")


def _set_snapshot_age(effective_at: datetime) -> None:
    effective = effective_at if effective_at.tzinfo else effective_at.replace(tzinfo=timezone.utc)
    age = max((datetime.now(timezone.utc) - effective).total_seconds(), 0.0)
    FX_RATE_AGE_SECONDS.set(age)


@router.get("/rates", response_model=RateTableResponse)
async def get_rate_table(
    _: dict = Depends(get_auth_principal),
    session: AsyncSession = Depends(get_session),
) -> RateTableResponse:
    response = await FxRateService(session).get_rate_table()
    _set_snapshot_age(response.effective_at)
    return response


@router.post("/convert", response_model=ConversionPreviewResponse)
async def preview_conversion(
    request: ConversionPreviewRequest,
    _: dict = Depends(get_auth_principal),
    session: AsyncSession = Depends(get_session),
) -> ConversionPreviewResponse:
    response = await FxRateService(session).preview_conversion(
        from_currency=request.from_currency,
        to_currency=request.to_currency,
        amount=request.amount,
    )
    _set_snapshot_age(response.effective_at)
    return response
