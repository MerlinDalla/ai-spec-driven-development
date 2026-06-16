from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from fund_transfer.models.account import Account
from fund_transfer.models.audit_log import AuditLogEntry, OperationType
from fund_transfer.models.notification import Notification
from fund_transfer.models.transfer import Transfer
from fund_transfer.repositories.notification_repository import NotificationRepository
from fund_transfer.schemas.notification import NotificationResponse


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = NotificationRepository(session)

    async def create_transfer_notifications(
        self,
        transfer: Transfer,
        sender_account: Account,
        recipient_account: Account,
        actor_identity: str | None = None,
        request_id: str | None = None,
    ) -> None:
        notifications = [
            Notification(
                id=uuid.uuid4(),
                recipient_account_number=sender_account.account_number,
                transfer_id=transfer.id,
                direction="sent",
                source_amount=transfer.source_amount,
                source_currency=transfer.source_currency,
                net_credited_amount=transfer.destination_amount,
                net_credited_currency=transfer.destination_currency,
            ),
            Notification(
                id=uuid.uuid4(),
                recipient_account_number=recipient_account.account_number,
                transfer_id=transfer.id,
                direction="received",
                source_amount=transfer.source_amount,
                source_currency=transfer.source_currency,
                net_credited_amount=transfer.destination_amount,
                net_credited_currency=transfer.destination_currency,
            ),
        ]
        for notification in notifications:
            await self._repo.create_notification(notification)
            audit = AuditLogEntry(
                id=uuid.uuid4(),
                operation_type=OperationType.notification_delivered.value,
                actor_identity=actor_identity or transfer.caller_id,
                affected_account_numbers=[notification.recipient_account_number],
                amount=notification.net_credited_amount,
                currency=notification.net_credited_currency,
                outcome="success",
                detail={"transfer_id": str(transfer.id), "direction": notification.direction},
                request_id=request_id,
            )
            self._session.add(audit)
            await self._session.flush()

    async def list_for_account(self, account_number: str, unread_only: bool) -> list[NotificationResponse]:
        notifications = await self._repo.list_for_account(account_number, unread_only)
        return [NotificationResponse.model_validate(notification, from_attributes=True) for notification in notifications]

    async def mark_read(self, notification_id: uuid.UUID, account_number: str) -> NotificationResponse:
        notification = await self._repo.mark_read(notification_id, account_number)
        return NotificationResponse.model_validate(notification, from_attributes=True)
