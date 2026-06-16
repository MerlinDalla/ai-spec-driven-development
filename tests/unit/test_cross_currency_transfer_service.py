from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from fund_transfer.core.exceptions import RateDeviationError, TransferLimitExceededError
from fund_transfer.models.account import AccountStatus
from fund_transfer.models.transfer import TransferStatus
from fund_transfer.schemas.fx import CrossCurrencyTransferRequest
from fund_transfer.services.cross_currency_transfer_service import CrossCurrencyTransferService


def make_snapshot(snapshot_id: uuid.UUID, rate: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=snapshot_id,
        effective_at=datetime.now(timezone.utc),
        is_stale=False,
        rates={"EUR": {"USD": rate}, "EUR": {"USD": rate}, "USD": {"USD": "1.0"}},
    )


def make_account(account_number: str, balance: Decimal, owner_id: str, currency: str = "EUR") -> MagicMock:
    account = MagicMock()
    account.account_number = account_number
    account.balance = balance
    account.owner_id = owner_id
    account.currency = currency
    account.status = AccountStatus.active.value
    return account


def make_transfer() -> MagicMock:
    transfer = MagicMock()
    transfer.id = uuid.uuid4()
    transfer.status = TransferStatus.pending.value
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


@pytest.mark.asyncio
async def test_state_machine_pending_processing_completed():
    session = AsyncMock()
    session.begin.return_value.__aenter__ = AsyncMock(return_value=None)
    session.begin.return_value.__aexit__ = AsyncMock(return_value=False)
    src = make_account("ACCT-1", Decimal("1000.0000"), "user-1")
    dst = make_account("ACCT-2", Decimal("100.0000"), "user-2", currency="USD")
    src_result = MagicMock()
    src_result.scalar_one_or_none.return_value = src
    dst_result = MagicMock()
    dst_result.scalar_one_or_none.return_value = dst
    session.execute = AsyncMock(side_effect=[src_result, dst_result])
    current_snapshot_id = uuid.uuid4()
    preview_snapshot_id = current_snapshot_id
    snapshot = SimpleNamespace(
        id=current_snapshot_id,
        effective_at=datetime.now(timezone.utc),
        is_stale=False,
        rates={"EUR": {"USD": "1.0850", "USD": "1.0850"}, "USD": {"USD": "1.0"}},
    )
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
        transfer_repo.update_transfer_status = AsyncMock(side_effect=[transfer, transfer])
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
                fx_snapshot_id=preview_snapshot_id,
            ),
            caller_id="user-1",
            idempotency_key="idem-1",
            request_id="req-1",
        )
    transfer_repo.create_cross_currency_transfer.assert_awaited_once()
    assert transfer_repo.update_transfer_status.await_args_list == [
        call(transfer.id, TransferStatus.processing.value, request_id="req-1"),
        call(transfer.id, TransferStatus.completed.value, request_id="req-1"),
    ]


@pytest.mark.asyncio
async def test_fee_calculation_correct_values():
    session = AsyncMock()
    with patch("fund_transfer.services.cross_currency_transfer_service.TransferRepository"), patch(
        "fund_transfer.services.cross_currency_transfer_service.FxRateRepository"
    ):
        service = CrossCurrencyTransferService(session)
    sending_fee, gross, receiving_fee, net, total = service._calculate_amounts(Decimal("100.0000"), Decimal("1.0850"))
    assert sending_fee == Decimal("0.5000")
    assert gross == Decimal("108.5000")
    assert receiving_fee == Decimal("0.3255")
    assert net == Decimal("108.1745")
    assert total == Decimal("100.5000")


@pytest.mark.asyncio
async def test_rate_deviation_detection_raises():
    session = AsyncMock()
    with patch("fund_transfer.services.cross_currency_transfer_service.TransferRepository"), patch(
        "fund_transfer.services.cross_currency_transfer_service.FxRateRepository"
    ):
        service = CrossCurrencyTransferService(session)
    with pytest.raises(RateDeviationError):
        service._check_rate_deviation(Decimal("1.0000"), Decimal("1.0200"), uuid.uuid4())


@pytest.mark.asyncio
async def test_per_tx_limit_raises():
    session = AsyncMock()
    with patch("fund_transfer.services.cross_currency_transfer_service.TransferRepository") as repo_cls, patch(
        "fund_transfer.services.cross_currency_transfer_service.FxRateRepository"
    ):
        repo_cls.return_value.get_daily_transfer_volume_usd = AsyncMock(return_value=Decimal("0"))
        service = CrossCurrencyTransferService(session)
    with pytest.raises(TransferLimitExceededError):
        await service._check_transfer_limits("ACCT-1", Decimal("50000.0001"))


@pytest.mark.asyncio
async def test_per_day_limit_raises():
    session = AsyncMock()
    with patch("fund_transfer.services.cross_currency_transfer_service.TransferRepository") as repo_cls, patch(
        "fund_transfer.services.cross_currency_transfer_service.FxRateRepository"
    ):
        repo_cls.return_value.get_daily_transfer_volume_usd = AsyncMock(return_value=Decimal("99999.0000"))
        service = CrossCurrencyTransferService(session)
    with pytest.raises(TransferLimitExceededError):
        await service._check_transfer_limits("ACCT-1", Decimal("2.0000"))


@pytest.mark.asyncio
async def test_aml_hook_called_for_transfers_at_threshold():
    session = AsyncMock()
    transfer = make_transfer()
    src = make_account("ACCT-1", Decimal("1000.0000"), "user-1")
    dst = make_account("ACCT-2", Decimal("100.0000"), "user-2", currency="USD")
    with patch("fund_transfer.services.cross_currency_transfer_service.TransferRepository") as repo_cls, patch(
        "fund_transfer.services.cross_currency_transfer_service.FxRateRepository"
    ):
        repo_cls.return_value.write_audit_log = AsyncMock(return_value=None)
        service = CrossCurrencyTransferService(session)
        await service._aml_kyc_check(transfer, src, dst, Decimal("10000.0000"), "req-1")
    repo_cls.return_value.write_audit_log.assert_awaited_once()
