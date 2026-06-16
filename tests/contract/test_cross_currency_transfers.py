from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from fund_transfer.api.middleware.auth import get_auth_principal
from fund_transfer.core.database import get_session
from fund_transfer.core.exceptions import (
    CapacityExceededError,
    ForbiddenError,
    InsufficientFundsError,
    NotFoundError,
    RateDeviationError,
    StaleRateError,
    TransferLimitExceededError,
    UnsupportedCurrencyPairError,
)
from fund_transfer.main import create_app
from fund_transfer.schemas.fx import CrossCurrencyTransferResponse
from fund_transfer.api.v1.transfers import check_transfer_capacity


def make_response() -> CrossCurrencyTransferResponse:
    return CrossCurrencyTransferResponse(
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
        fx_snapshot_id=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
    )


def build_client(capacity_exception: Exception | None = None):
    with patch("fund_transfer.main.Instrumentator") as instrumentator_cls:
        instrumentator_cls.return_value.instrument.return_value.expose.return_value = None
        app = create_app()
    session = AsyncMock()
    session.begin.return_value.__aenter__ = AsyncMock(return_value=None)
    session.begin.return_value.__aexit__ = AsyncMock(return_value=False)
    execute_result = MagicMock()
    execute_result.scalar_one.return_value = 0
    session.execute.return_value = execute_result

    async def override_session():
        yield session

    async def override_capacity():
        if capacity_exception is not None:
            raise capacity_exception
        return None

    app.dependency_overrides[get_auth_principal] = lambda: {"sub": "user-1"}
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[check_transfer_capacity] = override_capacity
    return TestClient(app, raise_server_exceptions=False)


def post_payload():
    return {
        "source_account_number": "ACCT-1",
        "destination_account_number": "ACCT-2",
        "source_amount": "100.0000",
        "source_currency": "EUR",
        "destination_currency": "USD",
        "fx_snapshot_id": str(uuid.uuid4()),
    }


def test_post_cross_currency_201_completed():
    with patch("fund_transfer.api.v1.transfers.CrossCurrencyTransferService") as svc_cls:
        svc_cls.return_value.initiate = AsyncMock(return_value=(make_response(), False))
        client = build_client()
        response = client.post("/api/v1/transfers/cross-currency", headers={"Authorization": "Bearer token", "X-Idempotency-Key": "idem-1"}, json=post_payload())
    assert response.status_code == 201


def test_post_idempotency_replay_200():
    with patch("fund_transfer.api.v1.transfers.CrossCurrencyTransferService") as svc_cls:
        svc_cls.return_value.initiate = AsyncMock(return_value=(make_response(), True))
        client = build_client()
        response = client.post("/api/v1/transfers/cross-currency", headers={"Authorization": "Bearer token", "X-Idempotency-Key": "idem-1"}, json=post_payload())
    assert response.status_code == 200


def test_post_409_rate_deviation():
    with patch("fund_transfer.api.v1.transfers.CrossCurrencyTransferService") as svc_cls:
        svc_cls.return_value.initiate = AsyncMock(side_effect=RateDeviationError("moved", Decimal("1"), Decimal("1.2"), Decimal("20"), "snap"))
        client = build_client()
        response = client.post("/api/v1/transfers/cross-currency", headers={"Authorization": "Bearer token", "X-Idempotency-Key": "idem-1"}, json=post_payload())
    assert response.status_code == 409


def test_post_422_insufficient_funds():
    with patch("fund_transfer.api.v1.transfers.CrossCurrencyTransferService") as svc_cls:
        svc_cls.return_value.initiate = AsyncMock(side_effect=InsufficientFundsError("insufficient"))
        client = build_client()
        response = client.post("/api/v1/transfers/cross-currency", headers={"Authorization": "Bearer token", "X-Idempotency-Key": "idem-1"}, json=post_payload())
    assert response.status_code == 422


def test_post_422_unsupported_pair():
    with patch("fund_transfer.api.v1.transfers.CrossCurrencyTransferService") as svc_cls:
        svc_cls.return_value.initiate = AsyncMock(side_effect=UnsupportedCurrencyPairError("unsupported"))
        client = build_client()
        response = client.post("/api/v1/transfers/cross-currency", headers={"Authorization": "Bearer token", "X-Idempotency-Key": "idem-1"}, json=post_payload())
    assert response.status_code == 422


def test_post_503_stale_rate():
    with patch("fund_transfer.api.v1.transfers.CrossCurrencyTransferService") as svc_cls:
        svc_cls.return_value.initiate = AsyncMock(side_effect=StaleRateError("stale"))
        client = build_client()
        response = client.post("/api/v1/transfers/cross-currency", headers={"Authorization": "Bearer token", "X-Idempotency-Key": "idem-1"}, json=post_payload())
    assert response.status_code == 503


def test_post_503_capacity_exceeded():
    client = build_client(capacity_exception=CapacityExceededError("full"))
    response = client.post("/api/v1/transfers/cross-currency", headers={"Authorization": "Bearer token", "X-Idempotency-Key": "idem-1"}, json=post_payload())
    assert response.status_code == 503


def test_post_422_transfer_limit_exceeded():
    with patch("fund_transfer.api.v1.transfers.CrossCurrencyTransferService") as svc_cls:
        svc_cls.return_value.initiate = AsyncMock(
            side_effect=TransferLimitExceededError("limit", "per_transaction", Decimal("50000"), Decimal("50001"))
        )
        client = build_client()
        response = client.post("/api/v1/transfers/cross-currency", headers={"Authorization": "Bearer token", "X-Idempotency-Key": "idem-1"}, json=post_payload())
    assert response.status_code == 422


def test_get_status_200():
    transfer_id = uuid.uuid4()
    with patch("fund_transfer.api.v1.transfers.CrossCurrencyTransferService") as svc_cls:
        svc_cls.return_value.get_status = AsyncMock(return_value=make_response())
        client = build_client()
        response = client.get(f"/api/v1/transfers/{transfer_id}/status", headers={"Authorization": "Bearer token"})
    assert response.status_code == 200


def test_get_status_404():
    transfer_id = uuid.uuid4()
    with patch("fund_transfer.api.v1.transfers.CrossCurrencyTransferService") as svc_cls:
        svc_cls.return_value.get_status = AsyncMock(side_effect=NotFoundError("not found", error_code="TRANSFER_NOT_FOUND"))
        client = build_client()
        response = client.get(f"/api/v1/transfers/{transfer_id}/status", headers={"Authorization": "Bearer token"})
    assert response.status_code == 404


def test_get_status_403_not_owner():
    transfer_id = uuid.uuid4()
    with patch("fund_transfer.api.v1.transfers.CrossCurrencyTransferService") as svc_cls:
        svc_cls.return_value.get_status = AsyncMock(side_effect=ForbiddenError("forbidden"))
        client = build_client()
        response = client.get(f"/api/v1/transfers/{transfer_id}/status", headers={"Authorization": "Bearer token"})
    assert response.status_code == 403
