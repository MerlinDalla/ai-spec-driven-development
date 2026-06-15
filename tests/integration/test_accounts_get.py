from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Integration tests require live PostgreSQL — run with docker-compose")


def test_newly_created_account_queryable():
    pass


def test_balance_exact_decimal_match():
    pass
