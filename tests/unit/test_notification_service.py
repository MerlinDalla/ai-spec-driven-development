from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fund_transfer.schemas.notification import NotificationResponse
from fund_transfer.services.notification_service import NotificationService


@pytest.mark.asyncio
async def test_create_transfer_notifications_creates_sender_and_recipient():
    session = MagicMock()
    session.flush = AsyncMock(return_value=None)
    transfer = SimpleNamespace(
        id=uuid.uuid4(),
        source_amount=Decimal("100.0000"),
        source_currency="EUR",
        destination_amount=Decimal("108.1745"),
        destination_currency="USD",
        caller_id="user-1",
    )
    sender = SimpleNamespace(account_number="ACCT-1")
    recipient = SimpleNamespace(account_number="ACCT-2")
    with patch("fund_transfer.services.notification_service.NotificationRepository") as repo_cls:
        repo_cls.return_value.create_notification = AsyncMock(return_value=None)
        service = NotificationService(session)
        await service.create_transfer_notifications(transfer, sender, recipient, actor_identity="user-1", request_id="req-1")
    assert repo_cls.return_value.create_notification.await_count == 2


@pytest.mark.asyncio
async def test_list_for_account_returns_responses():
    session = MagicMock()
    notification = SimpleNamespace(
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
    with patch("fund_transfer.services.notification_service.NotificationRepository") as repo_cls:
        repo_cls.return_value.list_for_account = AsyncMock(return_value=[notification])
        service = NotificationService(session)
        result = await service.list_for_account("ACCT-1", unread_only=True)
    assert result == [NotificationResponse.model_validate(notification, from_attributes=True)]


@pytest.mark.asyncio
async def test_mark_read_returns_response():
    session = MagicMock()
    notification = SimpleNamespace(
        id=uuid.uuid4(),
        recipient_account_number="ACCT-1",
        transfer_id=uuid.uuid4(),
        direction="received",
        source_amount=Decimal("100.0000"),
        source_currency="EUR",
        net_credited_amount=Decimal("108.1745"),
        net_credited_currency="USD",
        read_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    with patch("fund_transfer.services.notification_service.NotificationRepository") as repo_cls:
        repo_cls.return_value.mark_read = AsyncMock(return_value=notification)
        service = NotificationService(session)
        result = await service.mark_read(notification.id, "ACCT-1")
    assert result.id == notification.id
