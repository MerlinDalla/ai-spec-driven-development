from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: uuid.UUID
    recipient_account_number: str
    transfer_id: uuid.UUID
    direction: str
    source_amount: Decimal
    source_currency: str
    net_credited_amount: Decimal
    net_credited_currency: str
    read_at: datetime | None = None
    created_at: datetime
