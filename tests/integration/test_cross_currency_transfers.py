from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fund_transfer.models.account import AccountStatus
from fund_transfer.schemas.fx import CrossCurrencyTransferRequest
from fund_transfer.services.cross_currency_transfer_service import CrossCurrencyTransferService


def make_account(account_number: str, owner_id: str, currency: str, balance: Decimal) -> MagicMock:
    account = MagicMock()
    account.account_number = account_number
    account.owner_id = owner_id
    account.currency = currency
    account.balance = balance
    account.status = AccountStatus.active.value
    return account


def make_transfer() -> MagicMock:
    transfer = MagicMock()
    transfer.id = uuid.uuid4()
    transfer.status = "pending"
    transfer.source_amount = Decimal("100.0000")
    transfer.source_currency = "EUR"
    transfer.destination_amount = Decimal("108.1745")
    transfer.destination_currency = "USD"
    transfer.exchange_rate = Decimal("1.0850")
    transfer.sending_fee = Decimal("0.5000")
    transfer.receiving_fee = Decimal("0.3255")
    transfer.failure_reason = None
    transfer.fx_snapshot_id = uuid.uuid4()
    transfer.created_at = datetime.now(timezone.utc)
    transfer.caller_id = "user-1"
    return transfer


def make_snapshot(snapshot_id: uuid.UUID) -> SimpleNamespace:
    return SimpleNamespace(
        id=snapshot_id,
        effective_at=datetime.now(timezone.utc),
        is_stale=False,
        rates={"EUR": {"USD": "1.0850"}, "USD": {"USD": "1.0"}},
    )


@pytest.mark.asyncio
async def test_balance_conservation():
    session = AsyncMock()
    session.begin.return_value.__aenter__ = AsyncMock(return_value=None)
    session.begin.return_value.__aexit__ = AsyncMock(return_value=False)
    src = make_account("ACCT-1", "user-1", "EUR", Decimal("1000.0000"))
    dst = make_account("ACCT-2", "user-2", "USD", Decimal("50.0000"))
    src_result = MagicMock()
    src_result.scalar_one_or_none.return_value = src
    dst_result = MagicMock()
    dst_result.scalar_one_or_none.return_value = dst
    session.execute = AsyncMock(side_effect=[src_result, dst_result])
    snapshot_id = uuid.uuid4()
    snapshot = make_snapshot(snapshot_id)
    transfer = make_transfer()
    with patch("fund_transfer.services.cross_currency_transfer_service.FxRateRepository") as fx_repo_cls, patch(
        "fund_transfer.services.cross_currency_transfer_service.TransferRepository"
    ) as transfer_repo_cls, patch(
        "fund_transfer.services.cross_currency_transfer_service.NotificationService"
    ) as notification_cls:
        fx_repo = fx_repo_cls.return_value
        fx_repo.get_latest_snapshot = AsyncMock(return_value=snapshot)
        fx_repo.get_snapshot_by_id = AsyncMock(return_value=snapshot)
        fx_repo.get_active_currency_pairs = AsyncMock(return_value=[SimpleNamespace(from_currency="EUR", to_currency="USD")])
        transfer_repo = transfer_repo_cls.return_value
        transfer_repo.get_idempotency_record = AsyncMock(return_value=None)
        transfer_repo.get_daily_transfer_volume_usd = AsyncMock(return_value=Decimal("0"))
        transfer_repo.create_cross_currency_transfer = AsyncMock(return_value=transfer)
        transfer_repo.update_transfer_status = AsyncMock(return_value=transfer)
        transfer_repo.write_audit_log = AsyncMock(return_value=None)
        notification_cls.return_value.create_transfer_notifications = AsyncMock(return_value=None)
        service = CrossCurrencyTransferService(session)
        await service.initiate(
            CrossCurrencyTransferRequest(
                source_account_number="ACCT-1",
                destination_account_number="ACCT-2",
                source_amount=Decimal("100.0000"),
                source_currency="EUR",
                destination_currency="USD",
                fx_snapshot_id=snapshot_id,
            ),
            caller_id="user-1",
            idempotency_key="idem-1",
            request_id="req-1",
        )
    assert src.balance == Decimal("899.5000")
    assert dst.balance == Decimal("158.1745")


@pytest.mark.asyncio
async def test_idempotency_second_call_returns_same_transfer_without_changes():
    session = AsyncMock()
    transfer = make_transfer()
    with patch("fund_transfer.services.cross_currency_transfer_service.TransferRepository") as transfer_repo_cls, patch(
        "fund_transfer.services.cross_currency_transfer_service.FxRateRepository"
    ):
        transfer_repo_cls.return_value.get_idempotency_record = AsyncMock(return_value={"transfer": transfer, "status": transfer.status})
        service = CrossCurrencyTransferService(session)
        response, is_replay = await service.initiate(
            CrossCurrencyTransferRequest(
                source_account_number="ACCT-1",
                destination_account_number="ACCT-2",
                source_amount=Decimal("100.0000"),
                source_currency="EUR",
                destination_currency="USD",
                fx_snapshot_id=uuid.uuid4(),
            ),
            caller_id="user-1",
            idempotency_key="idem-1",
            request_id="req-1",
        )
    assert is_replay is True
    assert response.id == transfer.id


@pytest.mark.asyncio
async def test_notifications_created_atomically():
    session = AsyncMock()
    session.begin.return_value.__aenter__ = AsyncMock(return_value=None)
    session.begin.return_value.__aexit__ = AsyncMock(return_value=False)
    src = make_account("ACCT-1", "user-1", "EUR", Decimal("1000.0000"))
    dst = make_account("ACCT-2", "user-2", "USD", Decimal("50.0000"))
    src_result = MagicMock()
    src_result.scalar_one_or_none.return_value = src
    dst_result = MagicMock()
    dst_result.scalar_one_or_none.return_value = dst
    session.execute = AsyncMock(side_effect=[src_result, dst_result])
    snapshot_id = uuid.uuid4()
    snapshot = make_snapshot(snapshot_id)
    transfer = make_transfer()
    with patch("fund_transfer.services.cross_currency_transfer_service.FxRateRepository") as fx_repo_cls, patch(
        "fund_transfer.services.cross_currency_transfer_service.TransferRepository"
    ) as transfer_repo_cls, patch(
        "fund_transfer.services.cross_currency_transfer_service.NotificationService"
    ) as notification_cls:
        fx_repo = fx_repo_cls.return_value
        fx_repo.get_latest_snapshot = AsyncMock(return_value=snapshot)
        fx_repo.get_snapshot_by_id = AsyncMock(return_value=snapshot)
        fx_repo.get_active_currency_pairs = AsyncMock(return_value=[SimpleNamespace(from_currency="EUR", to_currency="USD")])
        transfer_repo = transfer_repo_cls.return_value
        transfer_repo.get_idempotency_record = AsyncMock(return_value=None)
        transfer_repo.get_daily_transfer_volume_usd = AsyncMock(return_value=Decimal("0"))
        transfer_repo.create_cross_currency_transfer = AsyncMock(return_value=transfer)
        transfer_repo.update_transfer_status = AsyncMock(return_value=transfer)
        transfer_repo.write_audit_log = AsyncMock(return_value=None)
        notification_service = notification_cls.return_value
        notification_service.create_transfer_notifications = AsyncMock(return_value=None)
        service = CrossCurrencyTransferService(session)
        await service.initiate(
            CrossCurrencyTransferRequest(
                source_account_number="ACCT-1",
                destination_account_number="ACCT-2",
                source_amount=Decimal("100.0000"),
                source_currency="EUR",
                destination_currency="USD",
                fx_snapshot_id=snapshot_id,
            ),
            caller_id="user-1",
            idempotency_key="idem-1",
            request_id="req-1",
        )
    notification_service.create_transfer_notifications.assert_awaited_once()
