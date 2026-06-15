from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fund_transfer.api.v1 import accounts, transfers
from fund_transfer.api.v1.router import api_router
from fund_transfer.schemas.account import AccountResponse, CreateAccountRequest
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


def test_api_router_includes_account_and_transfer_routes():
    app = FastAPI()
    app.include_router(api_router)
    client = TestClient(app)
    openapi = client.get("/openapi.json").json()

    assert "/api/v1/accounts" in openapi["paths"]
    assert "/api/v1/accounts/{account_number}" in openapi["paths"]
    assert "/api/v1/transfers" in openapi["paths"]
