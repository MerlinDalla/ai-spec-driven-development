from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from fund_transfer.api.middleware.auth import get_auth_principal
from fund_transfer.core.database import get_session
from fund_transfer.core.exceptions import ForbiddenError, NotFoundError
from fund_transfer.main import create_app
from fund_transfer.schemas.notification import NotificationResponse


def make_notification() -> NotificationResponse:
    return NotificationResponse(
        id=uuid.uuid4(),
        recipient_account_number="ACCT-1",
        transfer_id=uuid.uuid4(),
        direction="received",
        source_amount=Decimal("100.0000"),
        source_currency="EUR",
        net_credited_amount=Decimal("108.1745"),
        net_credited_currency="USD",
        read_at=None,
        created_at=datetime.now(timezone.utc),
    )


def build_client():
    with patch("fund_transfer.main.Instrumentator") as instrumentator_cls:
        instrumentator_cls.return_value.instrument.return_value.expose.return_value = None
        app = create_app()
    session = AsyncMock()
    session.begin.return_value.__aenter__ = AsyncMock(return_value=None)
    session.begin.return_value.__aexit__ = AsyncMock(return_value=False)

    async def override_session():
        yield session

    app.dependency_overrides[get_auth_principal] = lambda: {"sub": "user-1"}
    app.dependency_overrides[get_session] = override_session
    return TestClient(app, raise_server_exceptions=False)


def test_get_notifications_returns_list():
    with patch("fund_transfer.api.v1.notifications.NotificationService") as svc_cls:
        svc_cls.return_value.list_for_account = AsyncMock(return_value=[make_notification()])
        client = build_client()
        response = client.get("/api/v1/notifications?account_number=ACCT-1", headers={"Authorization": "Bearer token"})
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_notifications_with_unread_only():
    with patch("fund_transfer.api.v1.notifications.NotificationService") as svc_cls:
        svc_cls.return_value.list_for_account = AsyncMock(return_value=[make_notification()])
        client = build_client()
        response = client.get(
            "/api/v1/notifications?account_number=ACCT-1&unread_only=true",
            headers={"Authorization": "Bearer token"},
        )
    assert response.status_code == 200


def test_patch_mark_read_returns_200():
    notification = make_notification().model_copy(update={"read_at": datetime.now(timezone.utc)})
    with patch("fund_transfer.api.v1.notifications.NotificationService") as svc_cls:
        svc_cls.return_value.mark_read = AsyncMock(return_value=notification)
        client = build_client()
        response = client.patch(
            f"/api/v1/notifications/{notification.id}/read?account_number=ACCT-1",
            headers={"Authorization": "Bearer token"},
        )
    assert response.status_code == 200
    assert response.json()["read_at"] is not None


def test_patch_mark_read_404():
    with patch("fund_transfer.api.v1.notifications.NotificationService") as svc_cls:
        svc_cls.return_value.mark_read = AsyncMock(side_effect=NotFoundError("missing", error_code="NOTIFICATION_NOT_FOUND"))
        client = build_client()
        response = client.patch(
            f"/api/v1/notifications/{uuid.uuid4()}/read?account_number=ACCT-1",
            headers={"Authorization": "Bearer token"},
        )
    assert response.status_code == 404


def test_patch_mark_read_403():
    with patch("fund_transfer.api.v1.notifications.NotificationService") as svc_cls:
        svc_cls.return_value.mark_read = AsyncMock(side_effect=ForbiddenError("forbidden"))
        client = build_client()
        response = client.patch(
            f"/api/v1/notifications/{uuid.uuid4()}/read?account_number=ACCT-1",
            headers={"Authorization": "Bearer token"},
        )
    assert response.status_code == 403
