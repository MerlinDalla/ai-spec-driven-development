from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Contract tests require live service — run with docker-compose")


def test_create_account_201():
    """POST /api/v1/accounts → 201 with AccountResponse schema"""
    pass


def test_create_account_400_negative_balance():
    """POST /api/v1/accounts → 400 VALIDATION_ERROR for negative opening_balance"""
    pass


def test_create_account_400_unsupported_currency():
    """POST /api/v1/accounts → 400 UNSUPPORTED_CURRENCY for unknown currency"""
    pass


def test_create_account_400_missing_fields():
    """POST /api/v1/accounts → 400 for missing owner_id or currency"""
    pass


def test_create_account_401_no_jwt():
    """POST /api/v1/accounts → 401 for missing JWT"""
    pass
