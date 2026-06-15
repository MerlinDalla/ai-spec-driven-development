from __future__ import annotations

import re
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fund_transfer.core.exceptions import ValidationError, UnsupportedCurrencyError
from fund_transfer.models.account import Account, AccountStatus
from fund_transfer.repositories.account_repository import _generate_account_number
from fund_transfer.schemas.account import CreateAccountRequest
from fund_transfer.services.account_service import AccountService
from fund_transfer.services.exchange_rate_service import ExchangeRateService


ACCOUNT_NUMBER_PATTERN = re.compile(r"^ACCT-[A-Z0-9]{12}$")


def test_account_number_format():
    number = _generate_account_number()
    assert ACCOUNT_NUMBER_PATTERN.match(number), f"Invalid format: {number}"


def test_account_number_uniqueness():
    numbers = {_generate_account_number() for _ in range(1000)}
    assert len(numbers) > 990


def make_mock_account(
    account_number="ACCT-TESTACCOUNT1",
    owner_id="user-123",
    currency="EUR",
    balance=Decimal("1000.0000"),
    status="active",
):
    account = MagicMock(spec=Account)
    account.account_number = account_number
    account.owner_id = owner_id
    account.currency = currency
    account.balance = balance
    account.status = status
    account.created_at = MagicMock()
    account.created_at.isoformat.return_value = "2026-06-15T10:00:00+00:00"
    account.updated_at = None
    return account


@pytest.mark.asyncio
async def test_create_account_valid(exchange_rate_config):
    svc = AccountService(ExchangeRateService(exchange_rate_config))
    mock_session = AsyncMock()
    mock_session.begin.return_value.__aenter__ = AsyncMock(return_value=None)
    mock_session.begin.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_account = make_mock_account()

    with patch("fund_transfer.services.account_service.AccountRepository") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.create = AsyncMock(return_value=mock_account)
        result = await svc.create_account(
            request=CreateAccountRequest(owner_id="user-123", currency="EUR", opening_balance=Decimal("1000.0000")),
            actor_identity="user-123",
            request_id="req-1",
            session=mock_session,
        )

    assert result.balance == "1000.0000"
    assert result.currency == "EUR"


@pytest.mark.asyncio
async def test_create_account_negative_balance_raises(exchange_rate_config):
    svc = AccountService(ExchangeRateService(exchange_rate_config))
    mock_session = AsyncMock()
    with pytest.raises(Exception):
        CreateAccountRequest(owner_id="user-123", currency="EUR", opening_balance=Decimal("-1.0000"))


@pytest.mark.asyncio
async def test_create_account_unsupported_currency_raises(exchange_rate_config):
    svc = AccountService(ExchangeRateService(exchange_rate_config))
    mock_session = AsyncMock()
    with pytest.raises(UnsupportedCurrencyError):
        await svc.create_account(
            request=CreateAccountRequest(owner_id="user-123", currency="XYZ", opening_balance=Decimal("100.0000")),
            actor_identity="user-123",
            request_id=None,
            session=mock_session,
        )
