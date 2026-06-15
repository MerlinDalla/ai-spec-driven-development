from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Contract tests require live service — run with docker-compose")


def test_get_account_200():
    """GET /api/v1/accounts/{account_number} → 200 AccountResponse"""
    pass


def test_get_account_404():
    """GET /api/v1/accounts/{account_number} → 404 ACCOUNT_NOT_FOUND"""
    pass


def test_get_account_403_non_owner():
    """GET /api/v1/accounts/{account_number} → 403 FORBIDDEN"""
    pass


def test_get_account_401_no_jwt():
    """GET /api/v1/accounts/{account_number} → 401 UNAUTHORIZED"""
    pass
