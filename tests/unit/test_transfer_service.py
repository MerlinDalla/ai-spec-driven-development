from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fund_transfer.core.exceptions import (
    InsufficientFundsError,
    LimitExceededError,
    ValidationError,
)
from fund_transfer.models.account import Account, AccountStatus
from fund_transfer.models.transfer import Transfer, TransferStatus
from fund_transfer.schemas.transfer import CreateTransferRequest
from fund_transfer.services.exchange_rate_service import ExchangeRateService
from fund_transfer.services.transfer_service import TransferService


def make_mock_account(account_number, currency="EUR", balance=Decimal("1000.0000")):
    acc = MagicMock(spec=Account)
    acc.account_number = account_number
    acc.currency = currency
    acc.balance = balance
    acc.status = AccountStatus.active.value
    acc.id = MagicMock()
    acc.id.__str__ = lambda self: "00000000-0000-0000-0000-000000000001"
    return acc


def make_mock_transfer(src="ACCT-SRC000000001", dst="ACCT-DST000000002"):
    t = MagicMock(spec=Transfer)
    t.id = MagicMock()
    t.id.__str__ = lambda self: "00000000-0000-0000-0000-000000000099"
    t.source_account_number = src
    t.destination_account_number = dst
    t.source_amount = Decimal("100.0000")
    t.source_currency = "EUR"
    t.destination_amount = Decimal("100.0000")
    t.destination_currency = "EUR"
    t.exchange_rate = Decimal("1.00000000")
    t.status = TransferStatus.completed.value
    t.rejection_reason = None
    t.created_at = MagicMock()
    t.created_at.isoformat.return_value = "2026-06-15T10:00:00+00:00"
    return t


@pytest.mark.asyncio
async def test_valid_same_currency_transfer(exchange_rate_config):
    svc = TransferService(ExchangeRateService(exchange_rate_config))
    mock_session = AsyncMock()
    mock_session.begin.return_value.__aenter__ = AsyncMock(return_value=None)
    mock_session.begin.return_value.__aexit__ = AsyncMock(return_value=False)

    src_account = make_mock_account("ACCT-SRC000000001", "EUR", Decimal("1000.0000"))
    dst_account = make_mock_account("ACCT-DST000000002", "EUR", Decimal("500.0000"))

    execute_result_src = MagicMock()
    execute_result_src.scalar_one_or_none.return_value = src_account
    execute_result_dst = MagicMock()
    execute_result_dst.scalar_one_or_none.return_value = dst_account

    mock_session.execute = AsyncMock(side_effect=[
        execute_result_src,
        execute_result_dst,
    ])

    mock_transfer = make_mock_transfer()
    with patch("fund_transfer.services.transfer_service.TransferRepository") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.get_idempotency_record = AsyncMock(return_value=None)
        mock_repo.create_transfer = AsyncMock(return_value=mock_transfer)
        mock_repo.write_audit_log = AsyncMock(return_value=None)

        result, is_replay = await svc.execute_transfer(
            request=CreateTransferRequest(
                source_account_number="ACCT-SRC000000001",
                destination_account_number="ACCT-DST000000002",
                amount=Decimal("100.0000"),
            ),
            caller_id="user-123",
            idempotency_key="key-001",
            request_hash="hash-001",
            request_id="req-1",
            session=mock_session,
        )

    assert is_replay is False
    assert result.source_amount == "100.0000"


@pytest.mark.asyncio
async def test_zero_amount_raises_validation_error(exchange_rate_config):
    svc = TransferService(ExchangeRateService(exchange_rate_config))
    mock_session = AsyncMock()
    with patch("fund_transfer.services.transfer_service.TransferRepository") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.get_idempotency_record = AsyncMock(return_value=None)

        with pytest.raises(ValidationError):
            await svc.execute_transfer(
                request=CreateTransferRequest(
                    source_account_number="ACCT-SRC000000001",
                    destination_account_number="ACCT-DST000000002",
                    amount=Decimal("0.0000"),
                ),
                caller_id="user-123",
                idempotency_key="key-002",
                request_hash="hash-002",
                request_id=None,
                session=mock_session,
            )


@pytest.mark.asyncio
async def test_self_transfer_raises(exchange_rate_config):
    with pytest.raises(Exception):
        CreateTransferRequest(
            source_account_number="ACCT-SRC000000001",
            destination_account_number="ACCT-SRC000000001",
            amount=Decimal("100.0000"),
        )
