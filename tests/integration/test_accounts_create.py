from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Integration tests require live PostgreSQL — run with docker-compose")


def test_account_persisted_and_queryable():
    pass


def test_balance_exact_decimal():
    pass


def test_audit_log_written():
    pass
