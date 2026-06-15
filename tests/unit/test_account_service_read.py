from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fund_transfer.core.exceptions import ForbiddenError, NotFoundError
from fund_transfer.models.account import Account, AccountStatus
from fund_transfer.services.account_service import AccountService
from fund_transfer.services.exchange_rate_service import ExchangeRateService


def make_mock_account(owner_id="user-123", status="active", balance=Decimal("500.0000")):
    account = MagicMock(spec=Account)
    account.account_number = "ACCT-TESTACCOUNT1"
    account.owner_id = owner_id
    account.currency = "EUR"
    account.balance = balance
    account.status = status
    account.created_at = MagicMock()
    account.created_at.isoformat.return_value = "2026-06-15T10:00:00+00:00"
    account.updated_at = None
    return account


@pytest.mark.asyncio
async def test_get_account_found(exchange_rate_config):
    svc = AccountService(ExchangeRateService(exchange_rate_config))
    mock_session = AsyncMock()
    mock_account = make_mock_account()

    with patch("fund_transfer.services.account_service.AccountRepository") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.get_active_by_account_number = AsyncMock(return_value=mock_account)

        result = await svc.get_account(
            account_number="ACCT-TESTACCOUNT1",
            actor_identity="user-123",
            claims={"sub": "user-123"},
            session=mock_session,
        )

    assert result.account_number == "ACCT-TESTACCOUNT1"
    assert result.balance == "500.0000"


@pytest.mark.asyncio
async def test_get_account_not_found(exchange_rate_config):
    svc = AccountService(ExchangeRateService(exchange_rate_config))
    mock_session = AsyncMock()

    with patch("fund_transfer.services.account_service.AccountRepository") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.get_active_by_account_number = AsyncMock(
            side_effect=NotFoundError("Account not found.", error_code="ACCOUNT_NOT_FOUND")
        )
        with pytest.raises(NotFoundError):
            await svc.get_account(
                account_number="ACCT-NONEXISTENT",
                actor_identity="user-999",
                claims={"sub": "user-999"},
                session=mock_session,
            )


@pytest.mark.asyncio
async def test_get_account_forbidden_non_owner(exchange_rate_config):
    svc = AccountService(ExchangeRateService(exchange_rate_config))
    mock_session = AsyncMock()
    mock_account = make_mock_account(owner_id="user-123")

    with patch("fund_transfer.services.account_service.AccountRepository") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.get_active_by_account_number = AsyncMock(return_value=mock_account)

        with pytest.raises(ForbiddenError):
            await svc.get_account(
                account_number="ACCT-TESTACCOUNT1",
                actor_identity="user-999",
                claims={"sub": "user-999"},
                session=mock_session,
            )


@pytest.mark.asyncio
async def test_get_account_operator_allowed(exchange_rate_config):
    svc = AccountService(ExchangeRateService(exchange_rate_config))
    mock_session = AsyncMock()
    mock_account = make_mock_account(owner_id="user-123")

    with patch("fund_transfer.services.account_service.AccountRepository") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.get_active_by_account_number = AsyncMock(return_value=mock_account)

        result = await svc.get_account(
            account_number="ACCT-TESTACCOUNT1",
            actor_identity="operator-1",
            claims={"sub": "operator-1", "role": "operator"},
            session=mock_session,
        )
    assert result.account_number == "ACCT-TESTACCOUNT1"
