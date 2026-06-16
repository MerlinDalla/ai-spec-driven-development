from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fund_transfer.core.exceptions import ForbiddenError, NotFoundError
from fund_transfer.models.notification import Notification


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_notification(self, notification: Notification) -> None:
        self._session.add(notification)
        await self._session.flush()

    async def list_for_account(self, account_number: str, unread_only: bool = False) -> list[Notification]:
        query = select(Notification).where(Notification.recipient_account_number == account_number)
        if unread_only:
            query = query.where(Notification.read_at == None)
        query = query.order_by(Notification.created_at.desc())
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def count_unread(self, account_number: str) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(Notification).where(
                Notification.recipient_account_number == account_number,
                Notification.read_at == None,
            )
        )
        return result.scalar_one()

    async def mark_read(self, notification_id: uuid.UUID, account_number: str) -> Notification:
        result = await self._session.execute(select(Notification).where(Notification.id == notification_id))
        notification = result.scalar_one_or_none()
        if notification is None:
            raise NotFoundError("Notification not found.", error_code="NOTIFICATION_NOT_FOUND")
        if notification.recipient_account_number != account_number:
            raise ForbiddenError("You do not own this notification.", error_code="FORBIDDEN")
        notification.read_at = datetime.now(timezone.utc)
        await self._session.flush()
        await self._session.refresh(notification)
        return notification
