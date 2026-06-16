from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fund_transfer.api.v1 import accounts, fx, notifications, transfers
from fund_transfer.api.v1.router import api_router
from fund_transfer.schemas.account import AccountResponse, CreateAccountRequest
from fund_transfer.schemas.fx import CrossCurrencyTransferRequest, CrossCurrencyTransferResponse
from fund_transfer.schemas.notification import NotificationResponse
from fund_transfer.schemas.transfer import CreateTransferRequest, TransferResponse


@pytest.mark.asyncio
async def test_accounts_create_endpoint_delegates_to_service():
    request = CreateAccountRequest(owner_id="user-123", currency="eur", opening_balance=Decimal("10.0000"))
    expected = AccountResponse(
        account_number="ACCT-ABC123456789",
        owner_id="user-123",
        currency="EUR",
        balance="10.0000",
        status="active",
        created_at="2026-06-15T10:00:00+00:00",
    )

    with patch.object(accounts, "_account_service") as service:
        service.create_account = AsyncMock(return_value=expected)
        result = await accounts.create_account(
            request=request,
            auth_principal={"sub": "user-123"},
            session=MagicMock(),
            request_id="req-1",
        )

    assert result == expected
    service.create_account.assert_awaited_once()


@pytest.mark.asyncio
async def test_accounts_get_endpoint_delegates_to_service():
    expected = AccountResponse(
        account_number="ACCT-ABC123456789",
        owner_id="user-123",
        currency="EUR",
        balance="10.0000",
        status="active",
        created_at="2026-06-15T10:00:00+00:00",
    )

    with patch.object(accounts, "_account_service") as service:
        service.get_account = AsyncMock(return_value=expected)
        result = await accounts.get_account(
            account_number="ACCT-ABC123456789",
            auth_principal={"sub": "user-123"},
            session=MagicMock(),
            request_id="req-2",
        )

    assert result == expected
    service.get_account.assert_awaited_once()


@pytest.mark.asyncio
async def test_accounts_delete_endpoint_returns_204():
    with patch.object(accounts, "_account_service") as service:
        service.delete_account = AsyncMock(return_value=None)
        response = await accounts.delete_account(
            account_number="ACCT-ABC123456789",
            auth_principal={"sub": "user-123"},
            session=MagicMock(),
            request_id="req-3",
        )

    assert response.status_code == 204
    service.delete_account.assert_awaited_once()


@pytest.mark.asyncio
async def test_transfers_create_endpoint_returns_201_response():
    request = CreateTransferRequest(
        source_account_number="ACCT-SRC12345678",
        destination_account_number="ACCT-DST12345678",
        amount=Decimal("25.0000"),
    )
    expected = TransferResponse(
        transfer_id="00000000-0000-0000-0000-000000000001",
        source_account_number=request.source_account_number,
        destination_account_number=request.destination_account_number,
        source_amount="25.0000",
        source_currency="EUR",
        destination_amount="25.0000",
        destination_currency="EUR",
        exchange_rate="1.00000000",
        status="completed",
        created_at="2026-06-15T10:00:00+00:00",
    )

    with patch.object(transfers, "_transfer_service") as service:
        service.execute_transfer = AsyncMock(return_value=(expected, False))
        response = await transfers.create_transfer(
            request=request,
            x_idempotency_key="idem-1",
            auth_principal={"sub": "user-123"},
            session=MagicMock(),
            request_id="req-4",
        )

    assert response.status_code == 201
    assert response.headers["X-Idempotency-Replay"] == "false"
    assert response.headers["X-Request-ID"] == "req-4"
    service.execute_transfer.assert_awaited_once()


@pytest.mark.asyncio
async def test_transfers_create_endpoint_returns_200_on_replay():
    request = CreateTransferRequest(
        source_account_number="ACCT-SRC12345678",
        destination_account_number="ACCT-DST12345678",
        amount=Decimal("25.0000"),
    )
    expected = TransferResponse(
        transfer_id="00000000-0000-0000-0000-000000000001",
        source_account_number=request.source_account_number,
        destination_account_number=request.destination_account_number,
        source_amount="25.0000",
        source_currency="EUR",
        destination_amount="25.0000",
        destination_currency="EUR",
        exchange_rate="1.00000000",
        status="completed",
        created_at="2026-06-15T10:00:00+00:00",
    )

    with patch.object(transfers, "_transfer_service") as service:
        service.execute_transfer = AsyncMock(return_value=(expected, True))
        response = await transfers.create_transfer(
            request=request,
            x_idempotency_key="idem-2",
            auth_principal={"sub": "user-123"},
            session=MagicMock(),
            request_id=None,
        )

    assert response.status_code == 200
    assert response.headers["X-Idempotency-Replay"] == "true"


@pytest.mark.asyncio
async def test_fx_get_rates_endpoint_delegates_to_service():
    expected = MagicMock()
    expected.effective_at = datetime.now(timezone.utc)
    with patch("fund_transfer.api.v1.fx.FxRateService") as svc_cls:
        svc_cls.return_value.get_rate_table = AsyncMock(return_value=expected)
        result = await fx.get_rate_table(_={"sub": "user-1"}, session=MagicMock())
    assert result == expected


@pytest.mark.asyncio
async def test_cross_currency_transfer_endpoint_returns_201():
    request = CrossCurrencyTransferRequest(
        source_account_number="ACCT-SRC12345678",
        destination_account_number="ACCT-DST12345678",
        source_amount=Decimal("100.0000"),
        source_currency="EUR",
        destination_currency="USD",
        fx_snapshot_id=uuid.uuid4(),
    )
    expected = CrossCurrencyTransferResponse(
        id=uuid.uuid4(),
        status="completed",
        source_amount=Decimal("100.0000"),
        source_currency="EUR",
        sending_fee=Decimal("0.5000"),
        gross_converted_amount=Decimal("108.5000"),
        receiving_fee=Decimal("0.3255"),
        net_credited_amount=Decimal("108.1745"),
        destination_currency="USD",
        exchange_rate=Decimal("1.0850"),
        created_at=datetime.now(timezone.utc),
    )
    with patch("fund_transfer.api.v1.transfers.CrossCurrencyTransferService") as svc_cls:
        svc_cls.return_value.initiate = AsyncMock(return_value=(expected, False))
        response = await transfers.create_cross_currency_transfer(
            request=request,
            x_idempotency_key="idem-3",
            auth_principal={"sub": "user-123"},
            session=MagicMock(),
            request_id="req-5",
            _=None,
        )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_notifications_list_endpoint_delegates_to_service():
    expected = [
        NotificationResponse(
            id=uuid.uuid4(),
            recipient_account_number="ACCT-1",
            transfer_id=uuid.uuid4(),
            direction="received",
            source_amount=Decimal("100.0000"),
            source_currency="EUR",
            net_credited_amount=Decimal("108.1745"),
            net_credited_currency="USD",
            created_at=datetime.now(timezone.utc),
        )
    ]
    with patch("fund_transfer.api.v1.notifications.NotificationService") as svc_cls:
        svc_cls.return_value.list_for_account = AsyncMock(return_value=expected)
        result = await notifications.list_notifications(
            account_number="ACCT-1",
            unread_only=True,
            auth_principal={"sub": "user-1"},
            session=MagicMock(),
        )
    assert result == expected


def test_api_router_includes_all_routes():
    app = FastAPI()
    app.include_router(api_router)
    client = TestClient(app)
    openapi = client.get("/openapi.json").json()

    assert "/api/v1/accounts" in openapi["paths"]
    assert "/api/v1/accounts/{account_number}" in openapi["paths"]
    assert "/api/v1/transfers" in openapi["paths"]
    assert "/api/v1/transfers/cross-currency" in openapi["paths"]
    assert "/api/v1/transfers/{transfer_id}/status" in openapi["paths"]
    assert "/api/v1/fx/rates" in openapi["paths"]
    assert "/api/v1/fx/convert" in openapi["paths"]
    assert "/api/v1/notifications" in openapi["paths"]
