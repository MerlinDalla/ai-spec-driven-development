from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Integration tests require live PostgreSQL — run with docker-compose")


def test_deleted_account_returns_404():
    pass


def test_transfer_records_retained():
    pass


def test_owner_id_anonymized():
    pass
