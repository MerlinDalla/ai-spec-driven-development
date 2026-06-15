from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from fund_transfer.core import security


def test_get_jwks_client_caches_instance():
    security._jwks_client = None
    fake_client = MagicMock()
    with patch("fund_transfer.core.security._get_jwks_client", return_value=fake_client) as factory:
        assert security.get_jwks_client() is fake_client
        assert security.get_jwks_client() is fake_client
    factory.assert_called_once()
    security._jwks_client = None


def test_validate_token_decodes_jwt():
    fake_client = MagicMock()
    fake_client.get_signing_key_from_jwt.return_value = MagicMock(key="public-key")
    fake_settings = MagicMock(JWT_AUDIENCE="fund-transfer-service")

    with patch("fund_transfer.core.security.get_settings", return_value=fake_settings), patch(
        "fund_transfer.core.security.get_jwks_client", return_value=fake_client
    ), patch("fund_transfer.core.security.jwt.decode", return_value={"sub": "user-123"}) as decode:
        claims = security.validate_token("token")

    assert claims == {"sub": "user-123"}
    decode.assert_called_once()


def test_get_current_user_requires_credentials():
    with pytest.raises(HTTPException) as exc:
        security.get_current_user(None)

    assert exc.value.status_code == 401
    assert exc.value.detail["error_code"] == "UNAUTHORIZED"


def test_get_current_user_returns_claims_for_valid_token():
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
    with patch("fund_transfer.core.security.validate_token", return_value={"sub": "user-123"}):
        claims = security.get_current_user(credentials)

    assert claims == {"sub": "user-123"}


def test_get_current_user_rejects_invalid_token():
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
    with patch("fund_transfer.core.security.validate_token", side_effect=ValueError("bad token")):
        with pytest.raises(HTTPException) as exc:
            security.get_current_user(credentials)

    assert exc.value.status_code == 401
    assert exc.value.detail["error_code"] == "UNAUTHORIZED"


def test_is_operator_checks_role():
    assert security.is_operator({"role": "operator"}) is True
    assert security.is_operator({"role": "customer"}) is False
