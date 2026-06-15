from __future__ import annotations
import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from fund_transfer.core.config import get_settings

_http_bearer = HTTPBearer(auto_error=False)


def _get_jwks_client() -> PyJWKClient:
    settings = get_settings()
    return PyJWKClient(
        settings.JWKS_URI,
        cache_jwk_set=True,
        lifespan=3600,
    )


_jwks_client: PyJWKClient | None = None


def get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = _get_jwks_client()
    return _jwks_client


def validate_token(token: str) -> dict:
    settings = get_settings()
    client = get_jwks_client()
    signing_key = client.get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.JWT_AUDIENCE,
        options={"verify_exp": True},
    )
    return claims


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_http_bearer),
) -> dict:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "UNAUTHORIZED", "message": "Authentication required."},
        )
    try:
        return validate_token(credentials.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "UNAUTHORIZED", "message": "Invalid or expired token."},
        )


def is_operator(claims: dict) -> bool:
    return claims.get("role") == "operator"
