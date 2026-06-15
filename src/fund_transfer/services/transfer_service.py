from __future__ import annotations

import asyncio
import functools
import inspect
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fund_transfer.core.exceptions import (
    IdempotencyConflictError,
    InsufficientFundsError,
    LimitExceededError,
    NotFoundError,
    ValidationError,
)
from fund_transfer.models.account import Account, AccountStatus
from fund_transfer.models.audit_log import OperationType
from fund_transfer.models.transfer import TransferStatus
from fund_transfer.repositories.transfer_repository import TransferRepository
from fund_transfer.schemas.transfer import CreateTransferRequest, TransferResponse
from fund_transfer.services.exchange_rate_service import ExchangeRateService


def retry_on_deadlock(max_retries: int = 3, backoff_factor: float = 0.1):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    exc_name = type(exc).__name__
                    if "DeadlockDetected" in exc_name or "deadlock" in str(exc).lower():
                        last_exc = exc
                        if attempt < max_retries:
                            await asyncio.sleep(backoff_factor * (2 ** attempt))
                            continue
                    raise
            raise last_exc

        return wrapper

    return decorator


async def _begin_transaction(session: AsyncSession):
    transaction = session.begin()
    if inspect.isawaitable(transaction):
        transaction = await transaction
    return transaction


class TransferService:
    def __init__(self, exchange_rate_service: ExchangeRateService | None = None) -> None:
        self._fx = exchange_rate_service or ExchangeRateService()

    @retry_on_deadlock(max_retries=3, backoff_factor=0.1)
    async def execute_transfer(
        self,
        request: CreateTransferRequest,
        caller_id: str,
        idempotency_key: str,
        request_hash: str,
        request_id: str | None,
        session: AsyncSession,
    ) -> tuple[TransferResponse, bool]:
        if request.amount <= Decimal("0"):
            raise ValidationError("Transfer amount must be greater than zero.")

        repo = TransferRepository(session)

        existing = await repo.get_idempotency_record(idempotency_key)
        if existing is not None:
            transfer = existing["transfer"]
            if transfer.caller_id != caller_id:
                raise IdempotencyConflictError(
                    "Idempotency-Key was previously used by a different caller.",
                )
            return TransferResponse.from_orm_transfer(transfer), True

        async with await _begin_transaction(session):
            src_result = await session.execute(
                select(Account)
                .where(Account.account_number == request.source_account_number)
                .with_for_update()
            )
            source_account = src_result.scalar_one_or_none()
            if source_account is None or source_account.status != AccountStatus.active.value:
                raise NotFoundError(
                    f"Source account {request.source_account_number} does not exist.",
                    error_code="ACCOUNT_NOT_FOUND",
                )

            dst_result = await session.execute(
                select(Account)
                .where(Account.account_number == request.destination_account_number)
                .with_for_update()
            )
            dest_account = dst_result.scalar_one_or_none()
            if dest_account is None or dest_account.status != AccountStatus.active.value:
                raise NotFoundError(
                    f"Destination account {request.destination_account_number} does not exist.",
                    error_code="ACCOUNT_NOT_FOUND",
                )

            max_amount = self._fx.get_max_transfer_amount(source_account.currency)
            if request.amount > max_amount:
                raise LimitExceededError(
                    f"Transfer amount {request.amount:.4f} {source_account.currency} exceeds the "
                    f"maximum allowed per-transfer limit of {max_amount:.4f} {source_account.currency}.",
                )

            if source_account.balance < request.amount:
                raise InsufficientFundsError(
                    f"Source account has insufficient funds: balance {source_account.balance:.4f} "
                    f"{source_account.currency}, requested {request.amount:.4f} {source_account.currency}.",
                )

            exchange_rate = self._fx.get_rate(source_account.currency, dest_account.currency)
            destination_amount = (request.amount * exchange_rate).quantize(Decimal("0.0001"))

            source_account.balance = source_account.balance - request.amount
            dest_account.balance = dest_account.balance + destination_amount

            transfer = await repo.create_transfer(
                idempotency_key=idempotency_key,
                source_account_number=request.source_account_number,
                destination_account_number=request.destination_account_number,
                source_amount=request.amount,
                source_currency=source_account.currency,
                destination_amount=destination_amount,
                destination_currency=dest_account.currency,
                exchange_rate=exchange_rate,
                status=TransferStatus.completed.value,
                caller_id=caller_id,
            )

            await repo.write_audit_log(
                operation_type=OperationType.transfer_completed.value,
                actor_identity=caller_id,
                affected_account_numbers=[
                    request.source_account_number,
                    request.destination_account_number,
                ],
                amount=request.amount,
                currency=source_account.currency,
                outcome="success",
                detail={
                    "exchange_rate": str(exchange_rate),
                    "destination_amount": str(destination_amount),
                    "destination_currency": dest_account.currency,
                },
                request_id=request_id,
            )

        return TransferResponse.from_orm_transfer(transfer), False
