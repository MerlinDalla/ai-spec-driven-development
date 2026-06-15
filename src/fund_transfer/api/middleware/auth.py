from __future__ import annotations
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from fund_transfer.core.exceptions import ForbiddenError
from fund_transfer.core.security import get_current_user, is_operator

_http_bearer = HTTPBearer(auto_error=False)


def get_auth_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_http_bearer),
) -> dict:
    return get_current_user(credentials)


def require_owner_or_operator(account_owner_id: str, claims: dict) -> None:
    if claims.get("sub") != account_owner_id and not is_operator(claims):
        raise ForbiddenError("You are not authorized to access this account.")
