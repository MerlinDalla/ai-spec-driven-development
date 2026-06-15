from __future__ import annotations

import inspect

from sqlalchemy.ext.asyncio import AsyncSession

from fund_transfer.api.middleware.auth import require_owner_or_operator
from fund_transfer.core.exceptions import ValidationError
from fund_transfer.repositories.account_repository import AccountRepository
from fund_transfer.schemas.account import AccountResponse, CreateAccountRequest
from fund_transfer.services.exchange_rate_service import ExchangeRateService


async def _begin_transaction(session: AsyncSession):
    transaction = session.begin()
    if inspect.isawaitable(transaction):
        transaction = await transaction
    return transaction


class AccountService:
    def __init__(self, exchange_rate_service: ExchangeRateService | None = None) -> None:
        self._fx = exchange_rate_service or ExchangeRateService()

    async def create_account(
        self,
        request: CreateAccountRequest,
        actor_identity: str,
        request_id: str | None,
        session: AsyncSession,
    ) -> AccountResponse:
        self._fx.validate_currency(request.currency)
        if request.opening_balance < 0:
            raise ValidationError("Opening balance must be greater than or equal to zero.")

        repo = AccountRepository(session)
        async with await _begin_transaction(session):
            account = await repo.create(
                owner_id=request.owner_id,
                currency=request.currency,
                balance=request.opening_balance,
                actor_identity=actor_identity,
                request_id=request_id,
            )
        return AccountResponse.from_orm_account(account)

    async def get_account(
        self,
        account_number: str,
        actor_identity: str,
        claims: dict,
        session: AsyncSession,
    ) -> AccountResponse:
        repo = AccountRepository(session)
        account = await repo.get_active_by_account_number(account_number)
        require_owner_or_operator(account.owner_id, claims)
        return AccountResponse.from_orm_account(account)

    async def delete_account(
        self,
        account_number: str,
        actor_identity: str,
        claims: dict,
        request_id: str | None,
        session: AsyncSession,
    ) -> None:
        repo = AccountRepository(session)
        account = await repo.get_active_by_account_number(account_number)
        require_owner_or_operator(account.owner_id, claims)
        async with await _begin_transaction(session):
            await repo.delete_account(
                account_number=account_number,
                actor_identity=actor_identity,
                request_id=request_id,
            )
