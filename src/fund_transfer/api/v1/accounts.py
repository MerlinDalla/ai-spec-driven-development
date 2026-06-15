from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from fund_transfer.api.middleware.auth import get_auth_principal
from fund_transfer.core.database import get_session
from fund_transfer.schemas.account import AccountResponse, CreateAccountRequest
from fund_transfer.services.account_service import AccountService

router = APIRouter(prefix="/accounts", tags=["Accounts"])
_account_service = AccountService()


def _get_request_id(x_request_id: str | None = Header(default=None, alias="X-Request-ID")) -> str | None:
    return x_request_id


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    request: CreateAccountRequest,
    auth_principal: dict = Depends(get_auth_principal),
    session: AsyncSession = Depends(get_session),
    request_id: str | None = Depends(_get_request_id),
) -> AccountResponse:
    actor_identity = auth_principal.get("sub", "unknown")
    return await _account_service.create_account(
        request=request,
        actor_identity=actor_identity,
        request_id=request_id,
        session=session,
    )


@router.get("/{account_number}", response_model=AccountResponse)
async def get_account(
    account_number: str,
    auth_principal: dict = Depends(get_auth_principal),
    session: AsyncSession = Depends(get_session),
    request_id: str | None = Depends(_get_request_id),
) -> AccountResponse:
    actor_identity = auth_principal.get("sub", "unknown")
    return await _account_service.get_account(
        account_number=account_number,
        actor_identity=actor_identity,
        claims=auth_principal,
        session=session,
    )


@router.delete("/{account_number}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_number: str,
    auth_principal: dict = Depends(get_auth_principal),
    session: AsyncSession = Depends(get_session),
    request_id: str | None = Depends(_get_request_id),
) -> Response:
    actor_identity = auth_principal.get("sub", "unknown")
    await _account_service.delete_account(
        account_number=account_number,
        actor_identity=actor_identity,
        claims=auth_principal,
        request_id=request_id,
        session=session,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
