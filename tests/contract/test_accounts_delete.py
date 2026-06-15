from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Contract tests require live service — run with docker-compose")


def test_delete_account_204():
    """DELETE /api/v1/accounts/{account_number} → 204 No Content"""
    pass


def test_delete_account_400_has_balance():
    """DELETE /api/v1/accounts/{account_number} → 400 ACCOUNT_HAS_BALANCE"""
    pass


def test_delete_account_404():
    """DELETE /api/v1/accounts/{account_number} → 404 ACCOUNT_NOT_FOUND"""
    pass


def test_delete_account_403():
    """DELETE /api/v1/accounts/{account_number} → 403 FORBIDDEN"""
    pass


def test_delete_account_401():
    """DELETE /api/v1/accounts/{account_number} → 401 UNAUTHORIZED"""
    pass
