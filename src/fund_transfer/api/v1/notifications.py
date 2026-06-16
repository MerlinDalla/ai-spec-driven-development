from __future__ import annotations

import uuid
import inspect

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from fund_transfer.api.middleware.auth import get_auth_principal
from fund_transfer.core.database import get_session
from fund_transfer.schemas.notification import NotificationResponse
from fund_transfer.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


async def _begin_transaction(session: AsyncSession):
    transaction = session.begin()
    if inspect.isawaitable(transaction):
        transaction = await transaction
    return transaction


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    account_number: str,
    unread_only: bool = False,
    auth_principal: dict = Depends(get_auth_principal),
    session: AsyncSession = Depends(get_session),
) -> list[NotificationResponse]:
    _ = auth_principal
    svc = NotificationService(session)
    return await svc.list_for_account(account_number, unread_only)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: uuid.UUID,
    account_number: str,
    auth_principal: dict = Depends(get_auth_principal),
    session: AsyncSession = Depends(get_session),
) -> NotificationResponse:
    _ = auth_principal
    async with await _begin_transaction(session):
        svc = NotificationService(session)
        return await svc.mark_read(notification_id, account_number)
