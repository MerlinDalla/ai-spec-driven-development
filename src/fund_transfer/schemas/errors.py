from __future__ import annotations
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    request_id: str
    details: dict | None = None
