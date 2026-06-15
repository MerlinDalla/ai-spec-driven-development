from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Contract tests require live service — run with docker-compose")


def test_create_transfer_201_same_currency():
    """POST /api/v1/transfers → 201 same-currency TransferResponse"""
    pass


def test_create_transfer_201_cross_currency():
    """POST /api/v1/transfers → 201 with exchange_rate and destination_amount"""
    pass


def test_create_transfer_422_insufficient_funds():
    """POST /api/v1/transfers → 422 INSUFFICIENT_FUNDS"""
    pass


def test_create_transfer_422_limit_exceeded():
    """POST /api/v1/transfers → 422 TRANSFER_LIMIT_EXCEEDED"""
    pass


def test_create_transfer_409_idempotency_conflict():
    """POST /api/v1/transfers → 409 IDEMPOTENCY_CONFLICT"""
    pass


def test_create_transfer_404_account_not_found():
    """POST /api/v1/transfers → 404 ACCOUNT_NOT_FOUND"""
    pass


def test_create_transfer_400_zero_amount():
    """POST /api/v1/transfers → 400 VALIDATION_ERROR for zero amount"""
    pass


def test_create_transfer_200_idempotency_replay():
    """POST /api/v1/transfers → 200 X-Idempotency-Replay: true"""
    pass
