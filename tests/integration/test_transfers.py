from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Integration tests require live PostgreSQL — run with docker-compose")


def test_source_balance_decreases():
    pass


def test_destination_balance_increases():
    pass


def test_total_balance_conserved():
    pass


def test_idempotency_replay():
    pass
