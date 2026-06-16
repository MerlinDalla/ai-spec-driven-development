from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from fund_transfer.api.middleware.auth import get_auth_principal
from fund_transfer.core.database import get_session
from fund_transfer.main import create_app


def build_app(session_override):
    with patch("fund_transfer.main.Instrumentator") as instrumentator_cls:
        instrumentator_cls.return_value.instrument.return_value.expose.return_value = None
        app = create_app()

    async def override_session():
        yield session_override

    app.dependency_overrides[get_auth_principal] = lambda: {"sub": "test-user"}
    app.dependency_overrides[get_session] = override_session
    return app


def test_get_rates_200_with_auth():
    session = AsyncMock()
    snapshot = SimpleNamespace(
        id=uuid.uuid4(),
        effective_at=datetime.now(timezone.utc),
        is_stale=False,
        rates={"EUR": {"USD": "1.0850"}},
    )
    pairs = [SimpleNamespace(from_currency="EUR", to_currency="USD")]
    app = build_app(session)
    with patch("fund_transfer.services.fx_rate_service.FxRateRepository") as repo_cls:
        repo = repo_cls.return_value
        repo.get_latest_snapshot = AsyncMock(return_value=snapshot)
        repo.get_active_currency_pairs = AsyncMock(return_value=pairs)
        client = TestClient(app)
        response = client.get("/api/v1/fx/rates", headers={"Authorization": "Bearer token"})
    assert response.status_code == 200
    body = response.json()
    assert body["snapshot_id"] == str(snapshot.id)
    assert body["rates"][0]["from_currency"] == "EUR"


def test_get_rates_401_no_auth():
    with patch("fund_transfer.main.Instrumentator") as instrumentator_cls:
        instrumentator_cls.return_value.instrument.return_value.expose.return_value = None
        client = TestClient(create_app(), raise_server_exceptions=False)
    response = client.get("/api/v1/fx/rates")
    assert response.status_code == 401


def test_convert_200_valid_pair():
    session = AsyncMock()
    snapshot = SimpleNamespace(
        id=uuid.uuid4(),
        effective_at=datetime.now(timezone.utc),
        is_stale=False,
        rates={"EUR": {"USD": "1.0850"}},
    )
    pairs = [SimpleNamespace(from_currency="EUR", to_currency="USD")]
    app = build_app(session)
    with patch("fund_transfer.services.fx_rate_service.FxRateRepository") as repo_cls:
        repo = repo_cls.return_value
        repo.get_latest_snapshot = AsyncMock(return_value=snapshot)
        repo.get_active_currency_pairs = AsyncMock(return_value=pairs)
        client = TestClient(app)
        response = client.post(
            "/api/v1/fx/convert",
            headers={"Authorization": "Bearer token"},
            json={"from_currency": "EUR", "to_currency": "USD", "amount": "100.0000"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["estimated_sending_fee"] == "0.5000"
    assert body["estimated_receiving_fee"] == "0.3255"
    assert body["estimated_net_amount"] == "108.1745"


def test_convert_422_unsupported_pair():
    session = AsyncMock()
    snapshot = SimpleNamespace(
        id=uuid.uuid4(),
        effective_at=datetime.now(timezone.utc),
        is_stale=False,
        rates={"EUR": {"USD": "1.0850"}},
    )
    app = build_app(session)
    with patch("fund_transfer.services.fx_rate_service.FxRateRepository") as repo_cls:
        repo = repo_cls.return_value
        repo.get_latest_snapshot = AsyncMock(return_value=snapshot)
        repo.get_active_currency_pairs = AsyncMock(return_value=[])
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/v1/fx/convert",
            headers={"Authorization": "Bearer token"},
            json={"from_currency": "EUR", "to_currency": "JPY", "amount": "100.0000"},
        )
    assert response.status_code == 422
    assert response.json()["error_code"] == "UNSUPPORTED_CURRENCY_PAIR"


def test_convert_503_stale_rates():
    session = AsyncMock()
    app = build_app(session)
    with patch("fund_transfer.services.fx_rate_service.FxRateRepository") as repo_cls:
        repo = repo_cls.return_value
        repo.get_latest_snapshot = AsyncMock(return_value=None)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/v1/fx/convert",
            headers={"Authorization": "Bearer token"},
            json={"from_currency": "EUR", "to_currency": "USD", "amount": "100.0000"},
        )
    assert response.status_code == 503
    assert response.json()["error_code"] == "STALE_EXCHANGE_RATE"
