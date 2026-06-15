from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fund_transfer.core.exceptions import AccountHasBalanceError, ForbiddenError, NotFoundError
from fund_transfer.models.account import Account, AccountStatus
from fund_transfer.services.account_service import AccountService
from fund_transfer.services.exchange_rate_service import ExchangeRateService


def make_mock_account(owner_id="user-123", balance=Decimal("0.0000"), status="active"):
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
async def test_delete_zero_balance_succeeds(exchange_rate_config):
    svc = AccountService(ExchangeRateService(exchange_rate_config))
    mock_session = AsyncMock()
    mock_session.begin.return_value.__aenter__ = AsyncMock(return_value=None)
    mock_session.begin.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_account = make_mock_account(balance=Decimal("0.0000"))

    with patch("fund_transfer.services.account_service.AccountRepository") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.get_active_by_account_number = AsyncMock(return_value=mock_account)
        mock_repo.delete_account = AsyncMock(return_value=None)

        await svc.delete_account(
            account_number="ACCT-TESTACCOUNT1",
            actor_identity="user-123",
            claims={"sub": "user-123"},
            request_id="req-1",
            session=mock_session,
        )


@pytest.mark.asyncio
async def test_delete_non_zero_balance_raises(exchange_rate_config):
    svc = AccountService(ExchangeRateService(exchange_rate_config))
    mock_session = AsyncMock()
    mock_account = make_mock_account(balance=Decimal("100.0000"))

    with patch("fund_transfer.services.account_service.AccountRepository") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.get_active_by_account_number = AsyncMock(return_value=mock_account)
        mock_repo.delete_account = AsyncMock(
            side_effect=AccountHasBalanceError("Account has balance.", error_code="ACCOUNT_HAS_BALANCE")
        )
        mock_session.begin.return_value.__aenter__ = AsyncMock(return_value=None)
        mock_session.begin.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(AccountHasBalanceError):
            await svc.delete_account(
                account_number="ACCT-TESTACCOUNT1",
                actor_identity="user-123",
                claims={"sub": "user-123"},
                request_id=None,
                session=mock_session,
            )


@pytest.mark.asyncio
async def test_delete_unauthorized_raises(exchange_rate_config):
    svc = AccountService(ExchangeRateService(exchange_rate_config))
    mock_session = AsyncMock()
    mock_account = make_mock_account(owner_id="user-123")

    with patch("fund_transfer.services.account_service.AccountRepository") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.get_active_by_account_number = AsyncMock(return_value=mock_account)

        with pytest.raises(ForbiddenError):
            await svc.delete_account(
                account_number="ACCT-TESTACCOUNT1",
                actor_identity="user-999",
                claims={"sub": "user-999"},
                request_id=None,
                session=mock_session,
            )
