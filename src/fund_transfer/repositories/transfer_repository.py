from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fund_transfer.models.audit_log import AuditLogEntry
from fund_transfer.models.transfer import Transfer


class TransferRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_idempotency_record(self, key: str) -> dict | None:
        result = await self._session.execute(
            select(Transfer).where(Transfer.idempotency_key == key)
        )
        transfer = result.scalar_one_or_none()
        if transfer is None:
            return None
        return {
            "transfer": transfer,
            "status": transfer.status,
        }

    async def create_transfer(
        self,
        idempotency_key: str,
        source_account_number: str,
        destination_account_number: str,
        source_amount: Decimal,
        source_currency: str,
        destination_amount: Decimal,
        destination_currency: str,
        exchange_rate: Decimal,
        status: str,
        caller_id: str,
        rejection_reason: str | None = None,
    ) -> Transfer:
        transfer = Transfer(
            id=uuid.uuid4(),
            idempotency_key=idempotency_key,
            source_account_number=source_account_number,
            destination_account_number=destination_account_number,
            source_amount=source_amount,
            source_currency=source_currency,
            destination_amount=destination_amount,
            destination_currency=destination_currency,
            exchange_rate=exchange_rate,
            status=status,
            caller_id=caller_id,
            rejection_reason=rejection_reason,
        )
        self._session.add(transfer)
        await self._session.flush()
        await self._session.refresh(transfer)
        return transfer

    async def write_audit_log(
        self,
        operation_type: str,
        actor_identity: str,
        affected_account_numbers: list[str],
        amount: Decimal | None,
        currency: str | None,
        outcome: str,
        detail: dict | None,
        request_id: str | None,
    ) -> None:
        audit = AuditLogEntry(
            id=uuid.uuid4(),
            operation_type=operation_type,
            actor_identity=actor_identity,
            affected_account_numbers=affected_account_numbers,
            amount=amount,
            currency=currency,
            outcome=outcome,
            detail=detail,
            request_id=request_id,
        )
        self._session.add(audit)
        await self._session.flush()
