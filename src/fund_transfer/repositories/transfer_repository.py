from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fund_transfer.models.audit_log import AuditLogEntry, OperationType
from fund_transfer.models.transfer import Transfer, TransferStatus


class TransferRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_idempotency_record(self, key: str) -> dict | None:
        result = await self._session.execute(select(Transfer).where(Transfer.idempotency_key == key))
        transfer = result.scalar_one_or_none()
        if transfer is None:
            return None
        return {"transfer": transfer, "status": transfer.status}

    async def get_transfer_by_id(self, transfer_id: uuid.UUID) -> Transfer | None:
        result = await self._session.execute(select(Transfer).where(Transfer.id == transfer_id))
        return result.scalar_one_or_none()

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
        failure_reason: str | None = None,
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
            failure_reason=failure_reason if failure_reason is not None else rejection_reason,
        )
        self._session.add(transfer)
        await self._session.flush()
        await self._session.refresh(transfer)
        return transfer

    async def create_cross_currency_transfer(
        self,
        *,
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
        request_id: str | None,
        sending_fee: Decimal,
        sending_fee_currency: str,
        receiving_fee: Decimal,
        receiving_fee_currency: str,
        fx_snapshot_id: uuid.UUID,
        rate_confirmed_at: datetime,
        source_amount_usd: Decimal,
        failure_reason: str | None = None,
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
            failure_reason=failure_reason,
            transfer_type="cross_currency",
            sending_fee=sending_fee,
            sending_fee_currency=sending_fee_currency,
            receiving_fee=receiving_fee,
            receiving_fee_currency=receiving_fee_currency,
            fx_snapshot_id=fx_snapshot_id,
            rate_confirmed_at=rate_confirmed_at,
            source_amount_usd=source_amount_usd,
        )
        self._session.add(transfer)
        await self._session.flush()
        await self.write_audit_log(
            operation_type=OperationType.cross_currency_transfer_initiated.value,
            actor_identity=caller_id,
            affected_account_numbers=[source_account_number, destination_account_number],
            amount=source_amount,
            currency=source_currency,
            outcome="success",
            detail={
                "transfer_id": str(transfer.id),
                "fx_snapshot_id": str(fx_snapshot_id),
                "status": status,
                "sending_fee": str(sending_fee),
                "receiving_fee": str(receiving_fee),
            },
            request_id=request_id,
        )
        await self._session.refresh(transfer)
        return transfer

    async def update_transfer_status(
        self,
        transfer_id: uuid.UUID,
        new_status: str,
        failure_reason: str | None = None,
        request_id: str | None = None,
    ) -> Transfer:
        transfer = await self.get_transfer_by_id(transfer_id)
        if transfer is None:
            raise ValueError(f"Transfer {transfer_id} not found")

        allowed_transitions = {
            TransferStatus.pending.value: {TransferStatus.processing.value, TransferStatus.failed.value},
            TransferStatus.processing.value: {TransferStatus.completed.value, TransferStatus.failed.value},
            TransferStatus.completed.value: set(),
            TransferStatus.failed.value: set(),
            TransferStatus.rejected.value: set(),
        }
        if new_status != transfer.status and new_status not in allowed_transitions.get(transfer.status, set()):
            raise ValueError(f"Invalid status transition {transfer.status} -> {new_status}")

        transfer.status = new_status
        if failure_reason is not None:
            transfer.failure_reason = failure_reason
        await self._session.flush()

        operation_type = None
        if new_status == TransferStatus.completed.value:
            operation_type = OperationType.cross_currency_transfer_completed.value
        elif new_status == TransferStatus.failed.value:
            operation_type = OperationType.cross_currency_transfer_failed.value

        if operation_type is not None:
            await self.write_audit_log(
                operation_type=operation_type,
                actor_identity=transfer.caller_id,
                affected_account_numbers=[transfer.source_account_number, transfer.destination_account_number],
                amount=transfer.source_amount,
                currency=transfer.source_currency,
                outcome="success" if new_status == TransferStatus.completed.value else "failure",
                detail={
                    "transfer_id": str(transfer.id),
                    "status": new_status,
                    "failure_reason": transfer.failure_reason,
                },
                request_id=request_id,
            )
        await self._session.refresh(transfer)
        return transfer

    async def get_daily_transfer_volume_usd(self, account_number: str, since: datetime | None = None) -> Decimal:
        rolling_since = since or (datetime.now(timezone.utc) - timedelta(hours=24))
        result = await self._session.execute(
            select(func.coalesce(func.sum(Transfer.source_amount_usd), 0)).where(
                Transfer.source_account_number == account_number,
                Transfer.status.in_([TransferStatus.completed.value, TransferStatus.processing.value]),
                Transfer.created_at >= rolling_since,
            )
        )
        total = result.scalar_one()
        return Decimal(str(total or 0)).quantize(Decimal("0.0001"))

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
