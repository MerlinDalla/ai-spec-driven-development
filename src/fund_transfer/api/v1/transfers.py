from __future__ import annotations

import hashlib
import uuid

from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fund_transfer.api.middleware.auth import get_auth_principal
from fund_transfer.core.database import get_session
from fund_transfer.core.exceptions import CapacityExceededError
from fund_transfer.models.transfer import Transfer
from fund_transfer.schemas.fx import CrossCurrencyTransferRequest, CrossCurrencyTransferResponse
from fund_transfer.schemas.transfer import CreateTransferRequest
from fund_transfer.services.cross_currency_transfer_service import CrossCurrencyTransferService
from fund_transfer.services.transfer_service import TransferService

router = APIRouter(prefix="/transfers", tags=["Transfers"])
_transfer_service = TransferService()


def _get_request_id(x_request_id: str | None = Header(default=None, alias="X-Request-ID")) -> str | None:
    return x_request_id


async def check_transfer_capacity(session: AsyncSession = Depends(get_session)) -> None:
    result = await session.execute(
        select(func.count()).select_from(Transfer).where(Transfer.status.in_(["pending", "processing"]))
    )
    count = result.scalar_one()
    if count >= 500:
        raise CapacityExceededError("System at maximum transfer capacity; retry shortly.")


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_transfer(
    request: CreateTransferRequest,
    x_idempotency_key: str = Header(alias="X-Idempotency-Key", min_length=1, max_length=255),
    auth_principal: dict = Depends(get_auth_principal),
    session: AsyncSession = Depends(get_session),
    request_id: str | None = Depends(_get_request_id),
) -> Response:
    caller_id = auth_principal.get("sub", "unknown")
    request_body = request.model_dump_json()
    request_hash = hashlib.sha256(request_body.encode()).hexdigest()

    transfer_response, is_replay = await _transfer_service.execute_transfer(
        request=request,
        caller_id=caller_id,
        idempotency_key=x_idempotency_key,
        request_hash=request_hash,
        request_id=request_id,
        session=session,
    )

    http_status = status.HTTP_200_OK if is_replay else status.HTTP_201_CREATED
    headers = {
        "X-Idempotency-Replay": str(is_replay).lower(),
    }
    if request_id:
        headers["X-Request-ID"] = request_id

    return Response(
        content=transfer_response.model_dump_json(),
        status_code=http_status,
        headers=headers,
        media_type="application/json",
    )


@router.post("/cross-currency", response_model=CrossCurrencyTransferResponse, status_code=status.HTTP_201_CREATED)
async def create_cross_currency_transfer(
    request: CrossCurrencyTransferRequest,
    x_idempotency_key: str = Header(alias="X-Idempotency-Key", min_length=1, max_length=255),
    auth_principal: dict = Depends(get_auth_principal),
    session: AsyncSession = Depends(get_session),
    request_id: str | None = Depends(_get_request_id),
    _: None = Depends(check_transfer_capacity),
) -> Response:
    caller_id = auth_principal.get("sub", "unknown")
    transfer_response, is_replay = await CrossCurrencyTransferService(session).initiate(
        request=request,
        caller_id=caller_id,
        idempotency_key=x_idempotency_key,
        request_id=request_id,
    )
    http_status = status.HTTP_200_OK if is_replay else status.HTTP_201_CREATED
    headers = {"X-Idempotency-Replay": str(is_replay).lower()}
    if request_id:
        headers["X-Request-ID"] = request_id
    return Response(
        content=transfer_response.model_dump_json(),
        status_code=http_status,
        headers=headers,
        media_type="application/json",
    )


@router.get("/{transfer_id}/status", response_model=CrossCurrencyTransferResponse)
async def get_cross_currency_transfer_status(
    transfer_id: uuid.UUID,
    auth_principal: dict = Depends(get_auth_principal),
    session: AsyncSession = Depends(get_session),
) -> CrossCurrencyTransferResponse:
    caller_id = auth_principal.get("sub", "unknown")
    return await CrossCurrencyTransferService(session).get_status(transfer_id, caller_id)
