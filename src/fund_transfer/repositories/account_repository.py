from __future__ import annotations

import hashlib
import random
import string
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fund_transfer.core.exceptions import AccountHasBalanceError, NotFoundError
from fund_transfer.models.account import Account, AccountStatus
from fund_transfer.models.audit_log import AuditLogEntry, OperationType


def _generate_account_number() -> str:
    chars = string.ascii_uppercase + string.digits
    suffix = "".join(random.choices(chars, k=12))
    return f"ACCT-{suffix}"


class AccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        owner_id: str,
        currency: str,
        balance: Decimal,
        actor_identity: str,
        request_id: str | None = None,
    ) -> Account:
        for _ in range(10):
            account_number = _generate_account_number()
            existing = await self._session.execute(
                select(Account).where(Account.account_number == account_number)
            )
            if existing.scalar_one_or_none() is None:
                break

        account = Account(
            id=uuid.uuid4(),
            account_number=account_number,
            owner_id=owner_id,
            currency=currency,
            balance=balance,
            status=AccountStatus.active.value,
        )
        self._session.add(account)

        audit = AuditLogEntry(
            id=uuid.uuid4(),
            operation_type=OperationType.account_created.value,
            actor_identity=actor_identity,
            affected_account_numbers=[account_number],
            amount=balance,
            currency=currency,
            outcome="success",
            detail={"owner_id": owner_id},
            request_id=request_id,
        )
        self._session.add(audit)

        await self._session.flush()
        await self._session.refresh(account)
        return account

    async def get_by_account_number(self, account_number: str) -> Account | None:
        result = await self._session.execute(
            select(Account).where(Account.account_number == account_number)
        )
        return result.scalar_one_or_none()

    async def get_active_by_account_number(self, account_number: str) -> Account:
        result = await self._session.execute(
            select(Account).where(
                Account.account_number == account_number,
                Account.status == AccountStatus.active.value,
            )
        )
        account = result.scalar_one_or_none()
        if account is None:
            raise NotFoundError(
                f"Account {account_number} does not exist or is closed.",
                error_code="ACCOUNT_NOT_FOUND",
            )
        return account

    async def delete_account(
        self,
        account_number: str,
        actor_identity: str,
        request_id: str | None = None,
    ) -> None:
        result = await self._session.execute(
            select(Account).where(Account.account_number == account_number).with_for_update()
        )
        account = result.scalar_one_or_none()
        if account is None or account.status == AccountStatus.closed.value:
            raise NotFoundError(
                f"Account {account_number} does not exist.",
                error_code="ACCOUNT_NOT_FOUND",
            )
        if account.balance != Decimal("0"):
            raise AccountHasBalanceError(
                f"Account cannot be closed while it has a non-zero balance (current: {account.balance:.4f} {account.currency}).",
                error_code="ACCOUNT_HAS_BALANCE",
            )

        owner_hash = hashlib.sha256(account.owner_id.encode()).hexdigest()
        account.status = AccountStatus.closed.value
        account.owner_pii_hash = owner_hash
        account.owner_id = f"ANONYMIZED-{owner_hash[:16]}"

        audit = AuditLogEntry(
            id=uuid.uuid4(),
            operation_type=OperationType.account_deleted.value,
            actor_identity=actor_identity,
            affected_account_numbers=[account_number],
            amount=None,
            currency=account.currency,
            outcome="success",
            detail={"owner_pii_hash": owner_hash},
            request_id=request_id,
        )
        self._session.add(audit)
        await self._session.flush()
